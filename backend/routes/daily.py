from datetime import date

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from daily import (
    edition_number,
    is_match,
    rarity_multiplier,
    seconds_until_next_midnight_toronto,
    today_toronto,
)
from db import (
    count_daily_players,
    create_daily_challenge,
    daily_leaderboard,
    get_daily_challenge,
    get_db,
    get_or_create_daily_set,
    get_quote,
    new_challenge_code,
    quote_play_view,
    quote_reveal_view,
    upsert_daily_result,
)

router = APIRouter(prefix="/api/music-refs/daily", tags=["daily"])


class DailyAnswerIn(BaseModel):
    quote_id: int
    artist: str = ""
    title: str = ""
    date: str | None = None
    category_key: str = "all"


class DailyResultIn(BaseModel):
    player_id: str = Field(min_length=8, max_length=64)
    pseudo: str = ""
    score: int = Field(ge=0, le=5000)
    correct: int = Field(ge=0, le=5)
    hints: int = Field(ge=0, le=50)
    time_ms: int = Field(ge=0, le=3_600_000)
    grid: str = Field(default="", max_length=32)
    date: str | None = None
    category_id: int | None = None
    category_key: str | None = None


class ChallengeCreateIn(BaseModel):
    player_id: str = Field(min_length=8, max_length=64)
    pseudo: str = ""
    score: int = Field(ge=0, le=5000)
    correct: int = Field(ge=0, le=5)
    grid: str = Field(default="", max_length=32)
    date: str | None = None
    category_id: int | None = None
    category_key: str | None = None


def _resolve_category(
    conn,
    category_id: int | None = None,
    category: str | None = None,
) -> tuple[str, int | None, str]:
    """Resolve category_id or category slug/name → (key, id, display_name)."""
    if category_id is None and category:
        raw = category.strip()
        if raw.lower() in {"", "toutes", "all", "tous"}:
            return "all", None, "Toutes"
        if raw.isdigit():
            category_id = int(raw)
        else:
            row = conn.execute(
                "SELECT id, name FROM categories WHERE lower(slug) = lower(?) OR lower(name) = lower(?)",
                (raw, raw),
            ).fetchone()
            if not row:
                # fuzzy: "Rap" → "Rap français"
                row = conn.execute(
                    "SELECT id, name FROM categories WHERE lower(name) LIKE lower(?) OR lower(slug) LIKE lower(?)",
                    (f"%{raw}%", f"%{raw}%"),
                ).fetchone()
            if not row:
                raise HTTPException(404, f"Catégorie inconnue: {raw}")
            category_id = int(row["id"])

    if category_id is None:
        return "all", None, "Toutes"

    row = conn.execute("SELECT id, name FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Catégorie introuvable")
    return f"cat:{category_id}", category_id, row["name"]


def _reveals_for_set(conn, quote_ids: list[int]) -> list[dict]:
    out = []
    for qid in quote_ids:
        q = get_quote(conn, qid)
        if q:
            out.append(quote_reveal_view(q))
    return out


@router.get("")
def get_daily(
    category_id: int | None = Query(default=None),
    category: str | None = Query(default=None, description="slug, nom, id ou 'Toutes'"),
    date_str: str | None = Query(default=None, alias="date"),
):
    day = today_toronto()
    if date_str:
        try:
            day = date.fromisoformat(date_str)
        except ValueError as e:
            raise HTTPException(400, "date invalide (YYYY-MM-DD)") from e
    day_iso = day.isoformat()

    with get_db() as conn:
        cat_key, cat_id, cat_name = _resolve_category(conn, category_id, category)
        try:
            dset = get_or_create_daily_set(conn, day_iso, cat_key, cat_id)
        except ValueError:
            raise HTTPException(404, "Pas assez de punchlines pour cette catégorie") from None
        quotes = []
        for qid in dset["quote_ids"]:
            q = get_quote(conn, qid)
            if q:
                quotes.append(quote_play_view(q))

    return {
        "edition": dset["edition"],
        "date": day_iso,
        "category_key": cat_key,
        "category_id": cat_id,
        "category_name": cat_name,
        "quotes": quotes,
        "seconds_to_next": seconds_until_next_midnight_toronto() if day == today_toronto() else 0,
        "is_today": day == today_toronto(),
    }


@router.post("/answer")
def post_answer(body: DailyAnswerIn):
    day_iso = body.date or today_toronto().isoformat()
    with get_db() as conn:
        q = get_quote(conn, body.quote_id)
        if not q:
            raise HTTPException(404, "Citation introuvable")
        # Ensure quote belongs to today's set for this category
        dset = conn.execute(
            "SELECT quote_ids FROM daily_sets WHERE date = ? AND category_key = ?",
            (day_iso, body.category_key or "all"),
        ).fetchone()
        if dset:
            ids = json_ids(dset["quote_ids"])
            if body.quote_id not in ids:
                raise HTTPException(400, "Cette citation n'est pas dans le set du jour")

        artist_ok = is_match(body.artist, q["artist"]) if body.artist.strip() else False
        title_ok = is_match(body.title, q["title"]) if body.title.strip() else False
        # single field may match either
        if body.artist.strip() and not body.title.strip():
            if is_match(body.artist, q["title"]):
                title_ok = True
            if is_match(body.artist, q["artist"]):
                artist_ok = True

        points = 0
        if artist_ok:
            points += 100
        if title_ok:
            points += 100
        if artist_ok and title_ok:
            points += 50

        rarity = (q.get("rarity") or "commune").lower()
        mult = rarity_multiplier(rarity)
        points = int(round(points * mult))

        reveal = None
        if artist_ok and title_ok:
            reveal = {
                "artist": q["artist"],
                "title": q["title"],
                "listen_url": q.get("listen_url") or "",
                "rarity": rarity,
            }

        return {
            "artist_ok": artist_ok,
            "title_ok": title_ok,
            "fully_correct": artist_ok and title_ok,
            "points": points,
            "rarity": rarity,
            "multiplier": mult,
            "reveal": reveal,
        }


def json_ids(raw: str) -> list[int]:
    import json

    return [int(x) for x in json.loads(raw)]


@router.post("/result")
def post_result(body: DailyResultIn):
    day = today_toronto()
    if body.date:
        try:
            day = date.fromisoformat(body.date)
        except ValueError as e:
            raise HTTPException(400, "date invalide") from e
    day_iso = day.isoformat()

    # Anti-cheat light: reject absurdly fast completions
    if body.correct > 0 and body.time_ms < body.correct * 2000:
        raise HTTPException(400, "Temps trop court — score rejeté")

    ed = edition_number(day)
    with get_db() as conn:
        if body.category_key:
            cat_key = body.category_key
            cat_id = body.category_id
        else:
            cat_key, cat_id, _ = _resolve_category(conn, body.category_id, None)
        upsert_daily_result(
            conn,
            day_iso=day_iso,
            category_key=cat_key,
            edition=ed,
            player_id=body.player_id,
            pseudo=body.pseudo,
            score=body.score,
            correct=body.correct,
            hints=body.hints,
            time_ms=body.time_ms,
            grid=body.grid,
        )
        board = daily_leaderboard(conn, day_iso, cat_key, 10)
        total = count_daily_players(conn, day_iso, cat_key)
        # rank of this player
        rank = None
        rows = conn.execute(
            """
            SELECT player_id FROM daily_results
            WHERE date = ? AND category_key = ?
            ORDER BY score DESC, hints ASC, time_ms ASC
            """,
            (day_iso, cat_key),
        ).fetchall()
        for i, r in enumerate(rows, 1):
            if r["player_id"] == body.player_id:
                rank = i
                break

        reveals: list[dict] = []
        dset = conn.execute(
            "SELECT quote_ids FROM daily_sets WHERE date = ? AND category_key = ?",
            (day_iso, cat_key),
        ).fetchone()
        if dset:
            reveals = _reveals_for_set(conn, json_ids(dset["quote_ids"]))

    return {
        "ok": True,
        "rank": rank,
        "total_players": total,
        "leaderboard": board,
        "reveals": reveals,
        "seconds_to_next": seconds_until_next_midnight_toronto() if day == today_toronto() else 0,
    }


@router.get("/leaderboard")
def get_board(
    category_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    date_str: str | None = Query(default=None, alias="date"),
):
    day = today_toronto()
    if date_str:
        day = date.fromisoformat(date_str)
    day_iso = day.isoformat()
    with get_db() as conn:
        cat_key, _, _ = _resolve_category(conn, category_id, category)
        return {
            "date": day_iso,
            "category_key": cat_key,
            "total_players": count_daily_players(conn, day_iso, cat_key),
            "leaderboard": daily_leaderboard(conn, day_iso, cat_key, 10),
        }


@router.get("/reveal")
def get_reveal(
    category_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    date_str: str | None = Query(default=None, alias="date"),
    category_key: str | None = Query(default=None),
):
    """Révélation artiste/titre/listen_url — destinée à l'écran de fin (post-5e)."""
    day = today_toronto()
    if date_str:
        try:
            day = date.fromisoformat(date_str)
        except ValueError as e:
            raise HTTPException(400, "date invalide") from e
    day_iso = day.isoformat()
    with get_db() as conn:
        if category_key:
            cat_key = category_key
        else:
            cat_key, _, _ = _resolve_category(conn, category_id, category)
        dset = conn.execute(
            "SELECT quote_ids, edition FROM daily_sets WHERE date = ? AND category_key = ?",
            (day_iso, cat_key),
        ).fetchone()
        if not dset:
            raise HTTPException(404, "Set du jour introuvable")
        return {
            "date": day_iso,
            "category_key": cat_key,
            "edition": int(dset["edition"]),
            "reveals": _reveals_for_set(conn, json_ids(dset["quote_ids"])),
        }


@router.post("/challenge")
def post_challenge(body: ChallengeCreateIn):
    day = today_toronto()
    if body.date:
        try:
            day = date.fromisoformat(body.date)
        except ValueError as e:
            raise HTTPException(400, "date invalide") from e
    day_iso = day.isoformat()
    with get_db() as conn:
        if body.category_key:
            cat_key = body.category_key
            cat_id = body.category_id
        else:
            cat_key, cat_id, _ = _resolve_category(conn, body.category_id, None)
        code = new_challenge_code(conn)
        ch = create_daily_challenge(
            conn,
            code=code,
            day_iso=day_iso,
            category_key=cat_key,
            category_id=cat_id,
            creator_player_id=body.player_id,
            creator_pseudo=body.pseudo,
            creator_score=body.score,
            creator_correct=body.correct,
            creator_grid=body.grid,
        )
    return {
        "ok": True,
        "code": ch["code"],
        "url": f"/d/{ch['code']}",
        "challenge": ch,
    }


@router.get("/challenge/{code}")
def get_challenge(code: str):
    with get_db() as conn:
        ch = get_daily_challenge(conn, code.strip())
        if not ch:
            raise HTTPException(404, "Défi introuvable")
        return ch
