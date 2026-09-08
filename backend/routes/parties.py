from fastapi import APIRouter, HTTPException

from db import (
    create_party,
    get_db,
    join_party,
    party_quotes,
    party_snapshot,
    start_party,
    update_player_score,
)
from schemas import PartyCreate, PartyJoin, PartyScoreUpdate, PartyStart, QuoteOut

router = APIRouter(prefix="/api/music-refs/parties", tags=["parties"])


def _map_error(exc: ValueError):
    msg = str(exc)
    mapping = {
        "category_not_found": (404, "Category not found"),
        "category_empty": (400, "Category has no quotes"),
        "party_not_found": (404, "Party not found"),
        "party_not_joinable": (409, "Party already started or finished"),
        "name_taken": (409, "Player name already taken in this party"),
        "forbidden": (403, "Invalid host token"),
        "already_started": (409, "Party already started"),
        "not_started": (409, "Party not started yet"),
        "player_not_found": (404, "Player not found"),
    }
    code, detail = mapping.get(msg, (400, msg))
    raise HTTPException(status_code=code, detail=detail)


@router.post("")
def post_party(body: PartyCreate) -> dict:
    try:
        with get_db() as conn:
            return create_party(
                conn,
                category_id=body.category_id,
                host_name=body.host_name,
                round_limit=body.round_limit,
                mode=body.mode,
            )
    except ValueError as exc:
        _map_error(exc)


@router.post("/join")
def post_join(body: PartyJoin) -> dict:
    try:
        with get_db() as conn:
            return join_party(conn, code=body.code, player_name=body.player_name)
    except ValueError as exc:
        _map_error(exc)


@router.get("/{code}")
def get_party(code: str) -> dict:
    try:
        with get_db() as conn:
            return party_snapshot(conn, code)
    except ValueError as exc:
        _map_error(exc)


@router.post("/{code}/start")
def post_start(code: str, body: PartyStart) -> dict:
    try:
        with get_db() as conn:
            return start_party(conn, code=code, host_token=body.host_token)
    except ValueError as exc:
        _map_error(exc)


@router.get("/{code}/quotes", response_model=list[QuoteOut])
def get_party_quotes(code: str) -> list[QuoteOut]:
    try:
        with get_db() as conn:
            return [QuoteOut(**q) for q in party_quotes(conn, code)]
    except ValueError as exc:
        _map_error(exc)


@router.post("/{code}/score")
def post_score(code: str, body: PartyScoreUpdate) -> dict:
    try:
        with get_db() as conn:
            return update_player_score(
                conn,
                code=code,
                player_token=body.player_token,
                score=body.score,
                finished=body.finished,
                progress=body.progress,
            )
    except ValueError as exc:
        _map_error(exc)
