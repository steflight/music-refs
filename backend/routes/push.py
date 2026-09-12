"""MR-08 — abonnement Web Push (clé publique VAPID, subscribe, unsubscribe)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

import push
from db import delete_push_subscription, get_db, upsert_push_subscription
from schemas import PushPublicKeyOut, PushSubscribeIn, PushSubscribeOut, PushUnsubscribeIn

router = APIRouter(prefix="/api/music-refs/push", tags=["push"])

MSG_DISABLED = "Notifications push non configurées sur ce serveur"
MSG_BAD_TZ = "Fuseau horaire invalide (nom IANA attendu, ex. America/Toronto)"


@router.get("/public-key", response_model=PushPublicKeyOut)
def get_public_key() -> PushPublicKeyOut:
    return PushPublicKeyOut(
        enabled=push.is_configured(),
        public_key=push.public_key() if push.is_configured() else "",
        reminder_hour=push.reminder_hour(),
    )


@router.post("/subscribe", response_model=PushSubscribeOut)
def subscribe(body: PushSubscribeIn) -> PushSubscribeOut:
    if not push.is_configured():
        raise HTTPException(503, MSG_DISABLED)
    tz = push.valid_tz(body.tz)
    if not tz:
        raise HTTPException(422, MSG_BAD_TZ)
    with get_db() as conn:
        row = upsert_push_subscription(
            conn,
            player_id=body.player_id,
            endpoint=body.subscription.endpoint,
            p256dh=body.subscription.keys.p256dh,
            auth=body.subscription.keys.auth,
            tz=tz,
            streak=body.streak,
        )
    return PushSubscribeOut(ok=True, id=row["id"], tz=row["tz"], enabled=row["enabled"])


@router.delete("/subscribe")
def unsubscribe(body: PushUnsubscribeIn) -> dict:
    with get_db() as conn:
        deleted = delete_push_subscription(conn, body.endpoint)
    return {"ok": True, "deleted": deleted}
