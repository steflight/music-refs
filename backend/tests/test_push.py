"""Lot C — MR-08 rappel quotidien Web Push + MR-14 notification de défi.

Lancement : cd backend && python3 -m pytest tests/test_push.py -q
Base SQLite temporaire via DATABASE_PATH ; envoi push MOCKÉ (push.SENDER) ; clés VAPID factices.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

import config  # noqa: E402
import push  # noqa: E402
import ratelimit  # noqa: E402
from db import (  # noqa: E402
    get_db,
    get_or_create_daily_set,
    get_push_subscription,
    list_push_subscriptions,
    upsert_daily_result,
)
from main import app  # noqa: E402

TOKEN = "push-test-token"
ADMIN = {"X-Admin-Token": TOKEN}
PUB = "BKrPi8s6u7dnqEpi8ku1nDOQk89AAPb2zZnxI0INXoO51QktC-p7Wos9jGUg8PawCrki_mBB6N4586VwsvQKiJs"
PRIV = "test-private-key-not-used-because-sender-is-mocked"
_ENV_KEYS = (
    "DATABASE_PATH",
    "ADMIN_TOKEN",
    "RATE_LIMIT_PER_MINUTE",
    "VAPID_PUBLIC_KEY",
    "VAPID_PRIVATE_KEY",
    "VAPID_SUBJECT",
    "PUSH_SCHEDULER_ENABLED",
)
API = "/api/music-refs"


def _pid() -> str:
    return "p-" + uuid.uuid4().hex[:20]


def _endpoint() -> str:
    return f"https://fcm.googleapis.com/fcm/send/{uuid.uuid4().hex}"


def _sub_body(pid: str, endpoint: str | None = None, tz: str = "America/Toronto", **extra) -> dict:
    body = {
        "player_id": pid,
        "subscription": {
            "endpoint": endpoint or _endpoint(),
            "expirationTime": None,
            "keys": {"p256dh": "BPq0" + "x" * 80, "auth": "abcdefghijklmnop"},
        },
        "tz": tz,
    }
    body.update(extra)
    return body


class Recorder:
    """Remplace push.SENDER : enregistre les envois et renvoie un statut programmé."""

    def __init__(self) -> None:
        self.calls: list[tuple[dict, dict]] = []
        self.status = "ok"

    def __call__(self, sub: dict, payload: dict) -> str:
        self.calls.append((sub, payload))
        return self.status


class PushBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_env = {k: os.environ.get(k) for k in _ENV_KEYS}
        cls._tmp = tempfile.mkdtemp(prefix="mr-push-")
        os.environ["DATABASE_PATH"] = os.path.join(cls._tmp, "quotes.db")
        os.environ["ADMIN_TOKEN"] = TOKEN
        os.environ["RATE_LIMIT_PER_MINUTE"] = "0"
        os.environ["VAPID_PUBLIC_KEY"] = PUB
        os.environ["VAPID_PRIVATE_KEY"] = PRIV
        os.environ["VAPID_SUBJECT"] = "mailto:test@example.com"
        os.environ["PUSH_SCHEDULER_ENABLED"] = "0"
        config.get_settings.cache_clear()
        ratelimit.set_limit(0)
        ratelimit.reset()
        cls._saved_sender = push.SENDER
        cls._saved_sync = push.SYNC_DELIVERY
        push.SYNC_DELIVERY = True
        cls.client = TestClient(app)
        cls.client.__enter__()  # startup → init_db + seed (+ planificateur désactivé)

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        push.SENDER = cls._saved_sender
        push.SYNC_DELIVERY = cls._saved_sync
        ratelimit.set_limit(None)
        ratelimit.reset()
        for k, v in cls._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        config.get_settings.cache_clear()

    def setUp(self):
        self.rec = Recorder()
        push.SENDER = self.rec


# --- 1. abonnement + clé publique --------------------------------------------


class TestSubscribe(PushBase):
    def test_public_key(self):
        r = self.client.get(f"{API}/push/public-key")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["enabled"])
        self.assertEqual(data["public_key"], PUB)
        self.assertEqual(data["reminder_hour"], 19)

    def test_subscribe_update_unsubscribe(self):
        pid = _pid()
        endpoint = _endpoint()
        r = self.client.post(f"{API}/push/subscribe", json=_sub_body(pid, endpoint, tz="Europe/Paris"))
        self.assertEqual(r.status_code, 200, r.text)
        first = r.json()
        self.assertTrue(first["ok"] and first["enabled"])
        self.assertEqual(first["tz"], "Europe/Paris")

        # même endpoint → mise à jour (même id), fuseau + série mis à jour
        r = self.client.post(f"{API}/push/subscribe", json=_sub_body(pid, endpoint, tz="America/Toronto", streak=4))
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["id"], first["id"])
        self.assertEqual(r.json()["tz"], "America/Toronto")
        with get_db() as conn:
            row = get_push_subscription(conn, endpoint)
        self.assertIsNotNone(row)
        self.assertEqual(row["player_id"], pid)
        self.assertEqual(row["streak"], 4)
        self.assertIsNone(row["last_sent_day"])

        r = self.client.request("DELETE", f"{API}/push/subscribe", json={"endpoint": endpoint})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["deleted"])
        r = self.client.request("DELETE", f"{API}/push/subscribe", json={"endpoint": endpoint})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["deleted"])
        with get_db() as conn:
            self.assertIsNone(get_push_subscription(conn, endpoint))

    def test_subscribe_rejects_invalid_tz_and_endpoint(self):
        r = self.client.post(f"{API}/push/subscribe", json=_sub_body(_pid(), tz="Mars/Olympus"))
        self.assertEqual(r.status_code, 422)
        self.assertIn("Fuseau", r.json()["detail"])
        r = self.client.post(f"{API}/push/subscribe", json=_sub_body(_pid(), endpoint="http://insecure.example/x"))
        self.assertEqual(r.status_code, 422)


# --- 2. sélection pure due_subscriptions ---------------------------------------


class TestDueSubscriptions(unittest.TestCase):
    def rows(self, over: dict | None = None):
        base = [
            {"id": 1, "player_id": "a", "tz": "America/Toronto", "last_sent_day": None, "enabled": True},
            {"id": 2, "player_id": "b", "tz": "Europe/Paris", "last_sent_day": None, "enabled": True},
        ]
        for r in base:
            r.update((over or {}).get(r["id"], {}))
        return base

    def test_19h_toronto_only(self):
        # 23:00 UTC le 12 sept. = 19:00 EDT à Toronto, 01:00 le 13 à Paris
        now = datetime(2026, 9, 12, 23, 5, tzinfo=timezone.utc)
        due = push.due_subscriptions(now, self.rows(), 19)
        self.assertEqual([(r["id"], d) for r, d in due], [(1, "2026-09-12")])

    def test_19h_paris_only(self):
        # 17:00 UTC = 19:00 CEST à Paris, 13:00 à Toronto
        now = datetime(2026, 9, 12, 17, 0, tzinfo=timezone.utc)
        due = push.due_subscriptions(now, self.rows(), 19)
        self.assertEqual([(r["id"], d) for r, d in due], [(2, "2026-09-12")])

    def test_not_due_outside_hour(self):
        now = datetime(2026, 9, 12, 22, 59, tzinfo=timezone.utc)  # 18:59 Toronto
        self.assertEqual(push.due_subscriptions(now, self.rows(), 19), [])

    def test_already_sent_today_disabled_or_bad_tz(self):
        now = datetime(2026, 9, 12, 23, 30, tzinfo=timezone.utc)
        self.assertEqual(push.due_subscriptions(now, self.rows({1: {"last_sent_day": "2026-09-12"}}), 19), [])
        self.assertEqual(push.due_subscriptions(now, self.rows({1: {"enabled": False}}), 19), [])
        self.assertEqual(push.due_subscriptions(now, self.rows({1: {"tz": "Nulle/Part"}}), 19), [])
        # envoyé hier → dû aujourd'hui
        due = push.due_subscriptions(now, self.rows({1: {"last_sent_day": "2026-09-11"}}), 19)
        self.assertEqual([r["id"] for r, _ in due], [1])

    def test_naive_datetime_treated_as_utc(self):
        now = datetime(2026, 9, 12, 23, 0)
        self.assertEqual([r["id"] for r, _ in push.due_subscriptions(now, self.rows(), 19)], [1])


# --- 3. planificateur : run_tick ----------------------------------------------


def _complete_result(day_iso: str, pid: str) -> None:
    with get_db() as conn:
        dset = get_or_create_daily_set(conn, day_iso, "all", None)
        upsert_daily_result(
            conn, day_iso=day_iso, category_key="all", edition=1, player_id=pid, pseudo="",
            score=10, correct=1, hints=0, time_ms=60_000, grid="🟩⬛⬛⬛⬛", played=len(dset["quote_ids"]),
        )


class TestScheduler(PushBase):
    NOW = datetime(2026, 9, 12, 23, 1, tzinfo=timezone.utc)  # 19:01 à Toronto, jour 2026-09-12
    DAY = "2026-09-12"

    def _subscribe(self, pid: str, **extra) -> str:
        endpoint = _endpoint()
        r = self.client.post(f"{API}/push/subscribe", json=_sub_body(pid, endpoint, **extra))
        self.assertEqual(r.status_code, 200, r.text)
        return endpoint

    def test_reminder_sent_only_to_players_without_result(self):
        played, idle = _pid(), _pid()
        ep_played = self._subscribe(played)
        ep_idle = self._subscribe(idle)
        _complete_result(self.DAY, played)

        stats = push.run_tick_sync(self.NOW)
        sent_endpoints = [s["endpoint"] for s, _ in self.rec.calls]
        self.assertIn(ep_idle, sent_endpoints)
        self.assertNotIn(ep_played, sent_endpoints)
        self.assertEqual(stats["sent"], len(sent_endpoints))

        sub, payload = next(c for c in self.rec.calls if c[0]["endpoint"] == ep_idle)
        self.assertEqual(payload["body"], "🔥 Ta série expire dans 5 h. Les refs du jour t'attendent.")
        self.assertEqual(payload["url"], "/daily.html?ref=push")
        self.assertEqual(payload["title"], "Music Refs")

        with get_db() as conn:
            self.assertEqual(get_push_subscription(conn, ep_idle)["last_sent_day"], self.DAY)
            self.assertEqual(get_push_subscription(conn, ep_played)["last_sent_day"], self.DAY)

        # même tick une minute plus tard → plus rien
        self.rec.calls.clear()
        push.run_tick_sync(datetime(2026, 9, 12, 23, 2, tzinfo=timezone.utc))
        self.assertEqual(self.rec.calls, [])

    def test_reminder_text_includes_known_streak(self):
        pid = _pid()
        ep = self._subscribe(pid)
        _complete_result("2026-09-11", pid)
        _complete_result("2026-09-10", pid)
        push.run_tick_sync(self.NOW)
        payload = next(p for s, p in self.rec.calls if s["endpoint"] == ep)
        self.assertEqual(payload["body"], "🔥 Ta série de 2 jours expire dans 5 h. Les refs du jour t'attendent.")

    def test_client_streak_hint_wins_when_higher(self):
        pid = _pid()
        ep = self._subscribe(pid, streak=7)
        push.run_tick_sync(self.NOW)
        payload = next(p for s, p in self.rec.calls if s["endpoint"] == ep)
        self.assertIn("Ta série de 7 jours", payload["body"])

    def test_gone_endpoint_is_deleted(self):
        pid = _pid()
        ep = self._subscribe(pid)
        self.rec.status = "gone"
        stats = push.run_tick_sync(self.NOW)
        self.assertGreaterEqual(stats["gone"], 1)
        with get_db() as conn:
            self.assertIsNone(get_push_subscription(conn, ep))

    def test_not_19h_sends_nothing(self):
        self._subscribe(_pid())
        push.run_tick_sync(datetime(2026, 9, 12, 15, 0, tzinfo=timezone.utc))
        self.assertEqual(self.rec.calls, [])


# --- 4. MR-14 : hook défi -----------------------------------------------------


class TestChallengeHook(PushBase):
    DAY = "2026-08-01"

    def _play_all(self, pid: str) -> list[dict]:
        pack = self.client.get(f"{API}/daily", params={"date": self.DAY, "category": "all"}).json()
        admin = {q["id"]: q for q in self.client.get(f"{API}/quotes", headers=ADMIN).json()}
        out = []
        for q in pack["quotes"]:
            full = admin[q["id"]]
            r = self.client.post(
                f"{API}/daily/answer",
                json={
                    "quote_id": q["id"], "artist": full["artist"], "title": full["title"],
                    "date": self.DAY, "category_key": "all", "player_id": pid, "hints_used": 0,
                },
            )
            self.assertEqual(r.status_code, 200, r.text)
            out.append(r.json())
        return out

    def _result(self, pid: str, answers: list[dict], pseudo: str = "", **extra):
        body = {
            "player_id": pid, "pseudo": pseudo,
            "score": sum(a["score_delta"] for a in answers),
            "correct": sum(1 for a in answers if a["fully_correct"]),
            "hints": 0, "time_ms": 60_000, "grid": "", "date": self.DAY, "category_key": "all",
        }
        body.update(extra)
        return self.client.post(f"{API}/daily/result", json=body)

    def test_creator_notified_once_when_friend_completes(self):
        creator, friend = _pid(), _pid()
        ep = _endpoint()
        self.assertEqual(self.client.post(f"{API}/push/subscribe", json=_sub_body(creator, ep)).status_code, 200)

        ans = self._play_all(creator)
        r = self._result(creator, ans, pseudo="Lex")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json()["complete"])
        r = self.client.post(
            f"{API}/daily/challenge",
            json={"player_id": creator, "pseudo": "Lex", "score": 0, "correct": 0, "grid": "",
                  "date": self.DAY, "category_key": "all"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        code = r.json()["code"]
        self.assertEqual(self.rec.calls, [])  # créer un défi n'envoie rien

        # le créateur lui-même re-poste avec son code → rien
        r = self._result(creator, ans, pseudo="Lex", challenge_code=code)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.rec.calls, [])

        fans = self._play_all(friend)
        r = self._result(friend, fans, pseudo="Karim", challenge_code=code)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(self.rec.calls), 1)
        sub, payload = self.rec.calls[0]
        self.assertEqual(sub["endpoint"], ep)
        correct = r.json()["correct"]
        self.assertEqual(payload["body"], f"Karim a fait {correct}/5 sur ton défi 😱")
        self.assertIn(code, payload["url"])
        self.assertTrue(payload["url"].startswith("/daily.html?challenge="))

        # un seul envoi par défi : nouvel enregistrement du résultat → rien
        r = self._result(friend, fans, pseudo="Karim", challenge_code=code)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(len(self.rec.calls), 1)

    def test_unknown_or_incomplete_challenge_sends_nothing(self):
        friend = _pid()
        fans = self._play_all(friend)
        r = self._result(friend, fans, pseudo="Karim", challenge_code="ZZZZZZ")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(self.rec.calls, [])


# --- 5. démarrage sans clés ----------------------------------------------------


class TestNoKeys(PushBase):
    def setUp(self):
        super().setUp()
        os.environ["VAPID_PUBLIC_KEY"] = ""
        os.environ["VAPID_PRIVATE_KEY"] = ""
        config.get_settings.cache_clear()

    def tearDown(self):
        os.environ["VAPID_PUBLIC_KEY"] = PUB
        os.environ["VAPID_PRIVATE_KEY"] = PRIV
        config.get_settings.cache_clear()

    def test_service_runs_push_disabled(self):
        self.assertFalse(push.is_configured())
        self.assertEqual(self.client.get("/health").status_code, 200)
        r = self.client.get(f"{API}/push/public-key")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), {"enabled": False, "public_key": "", "reminder_hour": 19})
        r = self.client.post(f"{API}/push/subscribe", json=_sub_body(_pid()))
        self.assertEqual(r.status_code, 503)
        with self.assertLogs("music-refs.push", level="WARNING") as logs:
            self.assertFalse(push.start_scheduler())
        self.assertTrue(any("VAPID" in line for line in logs.output))
        self.assertEqual(push.run_tick_sync(datetime(2026, 9, 12, 23, 0, tzinfo=timezone.utc))["sent"], 0)
        self.assertEqual(push.deliver_to_player(_pid(), {"title": "x"}), 0)


if __name__ == "__main__":
    unittest.main()
