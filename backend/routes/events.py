"""MR-19 — collecte d'événements analytics (sans cookie tiers) et statistiques de la boucle."""

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query

from auth import require_admin
from daily import TZ
from db import EVENT_NAMES, EVENT_PROPS_MAX_BYTES, compute_stats, get_db, insert_events
from schemas import EventBatch, EventBatchOut

router = APIRouter(prefix="/api/music-refs", tags=["events"])

_PROPS_MAX_KEYS = 20
_PROPS_KEY_MAX = 32
_PROPS_STR_MAX = 200


def _clean_props(props: dict[str, Any]) -> dict[str, Any]:
    """Ne conserve que des scalaires courts (aucune structure imbriquée, aucun texte libre long)."""
    out: dict[str, Any] = {}
    for key, val in list(props.items())[:_PROPS_MAX_KEYS]:
        k = str(key)[:_PROPS_KEY_MAX]
        if isinstance(val, bool) or val is None:
            out[k] = val
        elif isinstance(val, (int, float)):
            out[k] = val
        elif isinstance(val, str):
            out[k] = val[:_PROPS_STR_MAX]
    return out


def _valid_tz(name: str) -> str:
    try:
        ZoneInfo(name)
        return name
    except Exception:
        return "UTC"


@router.post("/events", response_model=EventBatchOut)
def post_events(body: EventBatch) -> EventBatchOut:
    """Ingestion d'un lot (≤ 50) d'événements. Nom hors liste blanche ou props > 1 Ko → rejeté
    individuellement (compté dans `rejected`), le reste du lot est conservé. Horodatage serveur."""
    tz = _valid_tz(body.tz)
    accepted: list[tuple[str, dict[str, Any]]] = []
    rejected = 0
    for ev in body.events:
        if ev.name not in EVENT_NAMES:
            rejected += 1
            continue
        raw = ev.props or {}
        if len(json.dumps(raw, ensure_ascii=False, default=str).encode("utf-8")) > EVENT_PROPS_MAX_BYTES:
            rejected += 1
            continue
        props = _clean_props(raw)
        props["_tz"] = tz
        accepted.append((ev.name, props))
    now = datetime.now(TZ)
    day_iso = now.date().isoformat()
    if accepted:
        with get_db() as conn:
            insert_events(
                conn,
                player_id=body.player_id,
                items=accepted,
                ts=now.isoformat(timespec="seconds"),
                day=day_iso,
            )
    return EventBatchOut(accepted=len(accepted), rejected=rejected, day=day_iso)


@router.get("/stats", dependencies=[Depends(require_admin)])
def get_stats(days: int = Query(default=30, ge=1, le=365)) -> dict[str, Any]:
    """Statistiques de la boucle sur les `days` derniers jours (fenêtre = [aujourd'hui-days+1, aujourd'hui],
    jours calendaires America/Toronto, comme les Refs du jour). Protégé par X-Admin-Token.

    Réponse :
    {
      "days": 30, "from": "AAAA-MM-JJ", "to": "AAAA-MM-JJ", "timezone": "America/Toronto",
      "dau": {
        "today": int,          # joueurs distincts ayant daily_started OU daily_completed aujourd'hui
        "j7": int,             # idem il y a exactement 7 jours
        "avg": float,          # moyenne du DAU sur la fenêtre
        "series": [{"day": "AAAA-MM-JJ", "dau": int}, ...]   # un point par jour de la fenêtre
      },
      "retention": {           # cohorte = joueurs dont le PREMIER daily_completed tombe dans la fenêtre
        "j1":  {"cohort": int, "returned": int, "pct": float, "pct_or_later": float},
        "j7":  {...}, "j30": {...}
        # cohort  : joueurs de la cohorte dont J+n est déjà passé (cohorte « mûre »)
        # pct     : % de la cohorte mûre ayant un daily_completed EXACTEMENT le jour J+n
        # pct_or_later : % de la cohorte mûre ayant un daily_completed le jour J+n OU plus tard
      },
      "share": {
        "games": int,           # nb d'événements daily_completed sur la fenêtre
        "games_distinct": int,  # couples (joueur, jour) avec daily_completed
        "shared_distinct": int, # couples (joueur, jour) avec share_clicked
        "pct": float            # % de parties partagées = shared_distinct / games_distinct
      },
      "k_factor": float,        # share_landed / daily_completed (comptes bruts, fenêtre)
      "totals": {"<nom d'événement>": int, ...},   # tous les noms de la liste blanche, 0 si absent
      "by_day": [{"day": "AAAA-MM-JJ", "dau": int, "counts": {"<nom>": int, ...}}, ...]
    }
    """
    with get_db() as conn:
        return compute_stats(conn, days)
