"""MR-08 / MR-14 — Web Push (VAPID) : envoi, rappel quotidien planifié, notification de défi.

- Clés VAPID via `config.Settings` (VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY / VAPID_SUBJECT).
  Sans clés : `is_configured()` est faux, le service démarre, aucun envoi (log clair).
- `due_subscriptions(now_utc, rows, hour)` : sélection PURE des abonnements à rappeler
  (19 h locale dans le fuseau `tz`, pas encore envoyé ce jour-là).
- `run_tick(now_utc)` : une passe du planificateur (lecture base, envoi, marquage).
- `scheduler_loop()` : tâche asyncio lancée au démarrage de l'app, un tick par minute.
- `notify_challenge_completed(...)` : hook MR-14 appelé par POST /daily/result.

Les envois passent par `SENDER` (pywebpush) — remplaçable dans les tests. Résultat d'un
envoi : "ok" | "gone" (404/410 → abonnement supprimé) | "error".
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable
from zoneinfo import ZoneInfo

from config import get_settings
from db import (
    delete_push_subscription_by_id,
    get_db,
    has_complete_result_on_day,
    list_push_subscriptions,
    mark_push_sent,
    push_subscriptions_for_player,
    server_streak,
)

log = logging.getLogger("music-refs.push")

REMINDER_URL = "/daily.html?ref=push"
REMINDER_TAG = "daily-reminder"
CHALLENGE_TAG = "challenge"
TORONTO = ZoneInfo("America/Toronto")

# En tests : livraison synchrone (pas de thread) pour observer les appels.
SYNC_DELIVERY = False
_scheduler_task: asyncio.Task | None = None


# --- configuration ------------------------------------------------------------


def is_configured() -> bool:
    s = get_settings()
    return bool(s.vapid_public_key.strip() and s.vapid_private_key.strip())


def public_key() -> str:
    return get_settings().vapid_public_key.strip()


def reminder_hour() -> int:
    return int(get_settings().push_reminder_hour)


def valid_tz(name: str | None) -> str | None:
    """Nom IANA valide → tel quel ; sinon None."""
    if not name or not isinstance(name, str) or len(name) > 64:
        return None
    try:
        ZoneInfo(name)
    except Exception:
        return None
    return name


# --- messages -----------------------------------------------------------------


def reminder_payload(streak: int | None) -> dict[str, Any]:
    n = int(streak or 0)
    if n > 0:
        body = f"🔥 Ta série de {n} jour{'s' if n > 1 else ''} expire dans 5 h. Les refs du jour t'attendent."
    else:
        body = "🔥 Ta série expire dans 5 h. Les refs du jour t'attendent."
    return {"title": "Music Refs", "body": body, "url": REMINDER_URL, "tag": REMINDER_TAG}


def challenge_payload(friend_pseudo: str, correct: int, code: str) -> dict[str, Any]:
    who = (friend_pseudo or "").strip() or "Un ami"
    return {
        "title": "Music Refs — défi",
        "body": f"{who} a fait {int(correct)}/5 sur ton défi 😱",
        "url": f"/daily.html?challenge={code}&ref=push",
        "tag": f"{CHALLENGE_TAG}-{code}",
    }


# --- envoi --------------------------------------------------------------------


def _webpush_send(sub: dict[str, Any], payload: dict[str, Any]) -> str:
    """Envoi réel via pywebpush. Renvoie "ok" | "gone" | "error"."""
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:  # pragma: no cover - dépendance absente
        log.error("push: pywebpush absent — ajoute-le à requirements.txt")
        return "error"
    s = get_settings()
    try:
        webpush(
            subscription_info={"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=s.vapid_private_key.strip(),
            vapid_claims={"sub": s.vapid_subject.strip() or "mailto:contact@kladriva.ca"},
            ttl=6 * 3600,
            timeout=10,
        )
        return "ok"
    except WebPushException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (404, 410):
            return "gone"
        log.warning("push: échec d'envoi (%s) vers %s…", status or exc, sub["endpoint"][:60])
        return "error"
    except Exception as exc:  # réseau, encodage…
        log.warning("push: erreur d'envoi %r vers %s…", exc, sub["endpoint"][:60])
        return "error"


SENDER: Callable[[dict[str, Any], dict[str, Any]], str] = _webpush_send


def send_to_subscription(sub: dict[str, Any], payload: dict[str, Any]) -> str:
    """Envoie et nettoie l'abonnement si le service push répond 404/410."""
    if not is_configured():
        return "error"
    status = SENDER(sub, payload)
    if status == "gone":
        with get_db() as conn:
            delete_push_subscription_by_id(conn, int(sub["id"]))
        log.info("push: abonnement %s supprimé (endpoint expiré)", sub["id"])
    return status


def deliver_to_player(player_id: str, payload: dict[str, Any], background: bool | None = None) -> int:
    """Envoie `payload` à tous les abonnements actifs du joueur. Renvoie le nombre
    d'abonnements visés. En arrière-plan (thread) sauf SYNC_DELIVERY / background=False."""
    if not is_configured():
        return 0
    with get_db() as conn:
        subs = push_subscriptions_for_player(conn, player_id)
    if not subs:
        return 0

    def _run() -> None:
        for sub in subs:
            send_to_subscription(sub, payload)

    if background is None:
        background = not SYNC_DELIVERY
    if background:
        threading.Thread(target=_run, name="push-deliver", daemon=True).start()
    else:
        _run()
    return len(subs)


# --- MR-14 : hook défi ---------------------------------------------------------


def notify_challenge_completed(challenge: dict[str, Any], friend_pseudo: str, friend_correct: int) -> int:
    """Notifie le créateur du défi (s'il est abonné). L'unicité par défi est garantie
    par l'appelant via `db.mark_challenge_notified`."""
    payload = challenge_payload(friend_pseudo, friend_correct, challenge["code"])
    return deliver_to_player(challenge["creator_player_id"], payload)


# --- MR-08 : planificateur -------------------------------------------------------


def due_subscriptions(
    now_utc: datetime, rows: list[dict[str, Any]], hour: int = 19
) -> list[tuple[dict[str, Any], str]]:
    """Fonction PURE : abonnements dont l'heure locale (fuseau `tz`) est `hour` et qui
    n'ont pas encore reçu le rappel ce jour local. Renvoie [(row, jour_local_iso)].
    Fuseau invalide ou abonnement désactivé → ignoré."""
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    out: list[tuple[dict[str, Any], str]] = []
    for row in rows:
        if not row.get("enabled", True):
            continue
        tz = valid_tz(row.get("tz"))
        if not tz:
            continue
        local = now_utc.astimezone(ZoneInfo(tz))
        if local.hour != hour:
            continue
        day = local.date().isoformat()
        if row.get("last_sent_day") == day:
            continue
        out.append((row, day))
    return out


def _process_due(now_utc: datetime, due: list[tuple[dict[str, Any], str]]) -> list[dict[str, Any]]:
    """Filtre les joueurs ayant déjà un résultat complet aujourd'hui (date Toronto), marque
    `last_sent_day` et renvoie la liste [(sub, payload)] à envoyer."""
    toronto_day = now_utc.astimezone(TORONTO).date().isoformat()
    to_send: list[dict[str, Any]] = []
    with get_db() as conn:
        for sub, local_day in due:
            mark_push_sent(conn, int(sub["id"]), local_day)  # une seule tentative par jour
            if has_complete_result_on_day(conn, toronto_day, sub["player_id"]):
                continue
            streak = server_streak(conn, sub["player_id"], toronto_day)
            client_streak = sub.get("streak")
            if isinstance(client_streak, int) and client_streak > streak:
                streak = client_streak
            to_send.append({"sub": sub, "payload": reminder_payload(streak)})
    return to_send


def run_tick_sync(now_utc: datetime | None = None) -> dict[str, int]:
    """Une passe du planificateur, synchrone (appelée dans un thread par `run_tick`)."""
    if not is_configured():
        return {"due": 0, "sent": 0, "skipped": 0, "gone": 0, "error": 0}
    now_utc = now_utc or datetime.now(timezone.utc)
    with get_db() as conn:
        rows = list_push_subscriptions(conn, enabled_only=True)
    due = due_subscriptions(now_utc, rows, reminder_hour())
    to_send = _process_due(now_utc, due)
    stats = {"due": len(due), "sent": 0, "skipped": len(due) - len(to_send), "gone": 0, "error": 0}
    for item in to_send:
        status = send_to_subscription(item["sub"], item["payload"])
        if status == "ok":
            stats["sent"] += 1
        elif status == "gone":
            stats["gone"] += 1
        else:
            stats["error"] += 1
    if due:
        log.info("push: tick %s → %s", now_utc.isoformat(timespec="minutes"), stats)
    return stats


async def run_tick(now_utc: datetime | None = None) -> dict[str, int]:
    return await asyncio.to_thread(run_tick_sync, now_utc)


async def scheduler_loop() -> None:
    """Tick au début de chaque minute (aligné sur :00 s)."""
    while True:
        now = datetime.now(timezone.utc)
        await asyncio.sleep(60 - now.second - now.microsecond / 1_000_000)
        try:
            await run_tick()
        except asyncio.CancelledError:
            raise
        except Exception:  # ne jamais tuer la boucle
            log.exception("push: erreur dans le planificateur")


def start_scheduler() -> bool:
    """Lance la tâche asyncio (à appeler dans un handler de démarrage async)."""
    global _scheduler_task
    s = get_settings()
    if not is_configured():
        log.warning("push: VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY absentes — Web Push désactivé "
                    "(générer avec scripts/gen_vapid.py)")
        return False
    if not s.push_scheduler_enabled:
        log.info("push: planificateur désactivé (PUSH_SCHEDULER_ENABLED=0)")
        return False
    if _scheduler_task and not _scheduler_task.done():
        return True
    _scheduler_task = asyncio.get_event_loop().create_task(scheduler_loop(), name="push-scheduler")
    log.info("push: planificateur démarré (rappel à %d h locale)", reminder_hour())
    return True


async def stop_scheduler() -> None:
    global _scheduler_task
    task = _scheduler_task
    _scheduler_task = None
    if task and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
