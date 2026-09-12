import sqlite3

from fastapi import APIRouter, HTTPException

from db import (
    create_party,
    get_db,
    get_quote,
    join_party,
    party_quotes,
    party_snapshot,
    start_party,
    update_player_score,
)
from schemas import (
    PartyAnswerIn,
    PartyCreate,
    PartyJoin,
    PartyScoreUpdate,
    PartySkipIn,
    PartyStart,
    QuotePublicOut,
    QuoteReveal,
)
from scoring import BONUS_FULL, check_answer, compute_points, public_view

router = APIRouter(prefix="/api/music-refs/parties", tags=["parties"])

STREAK_STEP = 50  # bonus de série : (série - 1) × 50, comme l'ancien moteur local


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
        "quote_not_in_party": (400, "Cette punchline ne fait pas partie du salon"),
        "party_not_playing": (409, "Le salon n'est pas en cours de jeu"),
        "already_answered": (409, "Punchline déjà résolue"),
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


@router.get("/{code}/quotes", response_model=list[QuotePublicOut])
def get_party_quotes(code: str) -> list[QuotePublicOut]:
    """SEC-01 — punchlines du salon SANS artiste/titre/lien."""
    try:
        with get_db() as conn:
            return [QuotePublicOut(**public_view(q)) for q in party_quotes(conn, code)]
    except ValueError as exc:
        _map_error(exc)


# --- SEC-03 : réponses validées côté serveur ------------------------------


def _load_player_and_quote(
    conn: sqlite3.Connection, code: str, player_token: str, quote_id: int
) -> tuple[sqlite3.Row, sqlite3.Row, dict]:
    party = conn.execute("SELECT * FROM parties WHERE code = ?", (code.upper().strip(),)).fetchone()
    if not party:
        raise ValueError("party_not_found")
    if party["status"] != "playing":
        raise ValueError("party_not_playing")
    player = conn.execute(
        "SELECT * FROM party_players WHERE party_id = ? AND player_token = ?",
        (party["id"], player_token),
    ).fetchone()
    if not player:
        raise ValueError("player_not_found")
    in_party = conn.execute(
        "SELECT 1 FROM party_quotes WHERE party_id = ? AND quote_id = ?",
        (party["id"], quote_id),
    ).fetchone()
    if not in_party:
        raise ValueError("quote_not_in_party")
    quote = get_quote(conn, quote_id)
    if not quote:
        raise ValueError("quote_not_in_party")
    return party, player, quote


def _answer_row(conn: sqlite3.Connection, party_id: int, player_id: int, quote_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM party_answers WHERE party_id = ? AND player_id = ? AND quote_id = ?",
        (party_id, player_id, quote_id),
    ).fetchone()


def _upsert_answer(
    conn: sqlite3.Connection,
    party_id: int,
    player_id: int,
    quote_id: int,
    *,
    artist_ok: bool,
    title_ok: bool,
    forfeited: bool,
    points: int,
) -> None:
    conn.execute(
        """
        INSERT INTO party_answers (party_id, player_id, quote_id, artist_ok, title_ok, forfeited, points, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT(party_id, player_id, quote_id) DO UPDATE SET
            artist_ok = excluded.artist_ok,
            title_ok = excluded.title_ok,
            forfeited = excluded.forfeited,
            points = excluded.points,
            updated_at = excluded.updated_at
        """,
        (party_id, player_id, quote_id, int(artist_ok), int(title_ok), int(forfeited), int(points)),
    )


def _bump_player(conn: sqlite3.Connection, player_id: int, *, delta: int, streak: int) -> None:
    conn.execute(
        "UPDATE party_players SET score = MAX(0, score + ?), streak = ? WHERE id = ?",
        (int(delta), int(streak), player_id),
    )


@router.post("/{code}/answer")
def post_party_answer(code: str, body: PartyAnswerIn) -> dict:
    """Le client envoie sa réponse ; le serveur vérifie (MR-11) et attribue les points.

    `points` = total cumulé pour cette punchline (barème commun), `awarded` = points
    réellement ajoutés au score par cet appel (delta + bonus de série).
    """
    if not body.artist.strip() and not body.title.strip():
        raise HTTPException(status_code=400, detail="Saisissez au moins l'artiste ou le titre.")
    try:
        with get_db() as conn:
            party, player, quote = _load_player_and_quote(conn, code, body.player_token, body.quote_id)
            prev = _answer_row(conn, party["id"], player["id"], body.quote_id)
            prev_artist = bool(prev["artist_ok"]) if prev else False
            prev_title = bool(prev["title_ok"]) if prev else False
            prev_points = int(prev["points"]) if prev else 0
            forfeited = bool(prev["forfeited"]) if prev else False
            if prev_artist and prev_title:
                raise ValueError("already_answered")

            artist_ok, title_ok = check_answer(quote, body.artist, body.title)
            artist_ok = artist_ok or prev_artist
            title_ok = title_ok or prev_title
            newly = (artist_ok and not prev_artist) or (title_ok and not prev_title)
            streak = int(player["streak"] if "streak" in player.keys() else 0)
            awarded = 0
            points = prev_points
            if forfeited:
                # Réponse révélée par « Passer » : plus aucun point pour cette punchline.
                newly = False
            elif newly:
                points, _ = compute_points(artist_ok, title_ok, body.hints_used, quote.get("rarity"))
                awarded = max(0, points - prev_points)
                if artist_ok and title_ok:
                    streak += 1
                    awarded += (streak - 1) * STREAK_STEP
                _upsert_answer(
                    conn, party["id"], player["id"], body.quote_id,
                    artist_ok=artist_ok, title_ok=title_ok, forfeited=False, points=points,
                )
                _bump_player(conn, player["id"], delta=awarded, streak=streak)
            elif not artist_ok and not title_ok:
                streak = 0
                _bump_player(conn, player["id"], delta=0, streak=0)

            fully = artist_ok and title_ok
            half = artist_ok and not title_ok
            if forfeited:
                message = "Réponse déjà révélée : aucun point."
            elif fully:
                message = f"Artiste trouvé: {quote['artist']} | Titre trouvé: {quote['title']}"
            elif half:
                message = f"Artiste juste ({quote['artist']}), titre faux : moitié des points."
            elif title_ok:
                message = f"Titre trouvé: {quote['title']} — il manque l'artiste."
            else:
                message = "Mauvaise réponse. Réessayez !"
            snapshot = party_snapshot(conn, party["code"], include_tokens_for=body.player_token)
            me = snapshot.get("me") or {}
            return {
                "artist_ok": artist_ok,
                "title_ok": title_ok,
                "fully_correct": fully,
                "newly_correct": newly,
                "half_points": half,
                "points": points,
                "awarded": awarded,
                "score": int(me.get("score", 0)),
                "streak": streak,
                "message": message,
                "reveal": {
                    "artist": quote["artist"],
                    "title": quote["title"],
                    "listen_url": quote.get("listen_url") or "",
                } if fully else None,
                "party": snapshot,
            }
    except ValueError as exc:
        _map_error(exc)


@router.post("/{code}/skip")
def post_party_skip(code: str, body: PartySkipIn) -> dict:
    """« Passer » : révèle la réponse au joueur, gèle la punchline (0 point) et casse la série."""
    try:
        with get_db() as conn:
            party, player, quote = _load_player_and_quote(conn, code, body.player_token, body.quote_id)
            prev = _answer_row(conn, party["id"], player["id"], body.quote_id)
            if not (prev and prev["artist_ok"] and prev["title_ok"]):
                _upsert_answer(
                    conn, party["id"], player["id"], body.quote_id,
                    artist_ok=bool(prev["artist_ok"]) if prev else False,
                    title_ok=bool(prev["title_ok"]) if prev else False,
                    forfeited=True,
                    points=int(prev["points"]) if prev else 0,
                )
                _bump_player(conn, player["id"], delta=0, streak=0)
            snapshot = party_snapshot(conn, party["code"], include_tokens_for=body.player_token)
            return {
                "reveal": QuoteReveal(
                    artist=quote["artist"], title=quote["title"], listen_url=quote.get("listen_url") or ""
                ).model_dump(),
                "score": int((snapshot.get("me") or {}).get("score", 0)),
                "streak": 0,
                "party": snapshot,
            }
    except ValueError as exc:
        _map_error(exc)


@router.post("/{code}/score")
def post_score(code: str, body: PartyScoreUpdate) -> dict:
    """Progression / fin de partie uniquement : le `score` envoyé par le client est ignoré (SEC-03)."""
    try:
        with get_db() as conn:
            party = conn.execute("SELECT id FROM parties WHERE code = ?", (code.upper().strip(),)).fetchone()
            if not party:
                raise ValueError("party_not_found")
            player = conn.execute(
                "SELECT score FROM party_players WHERE party_id = ? AND player_token = ?",
                (party["id"], body.player_token),
            ).fetchone()
            if not player:
                raise ValueError("player_not_found")
            return update_player_score(
                conn,
                code=code,
                player_token=body.player_token,
                score=int(player["score"]),
                finished=body.finished,
                progress=body.progress,
            )
    except ValueError as exc:
        _map_error(exc)
