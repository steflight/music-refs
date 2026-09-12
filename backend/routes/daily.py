import time
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from daily import (
    MIN_MS_PER_QUOTE,
    answer_points,
    answer_score,
    edition_number,
    grid_cell,
    hint_cost,
    is_match,
    rarity_multiplier,
    seconds_until_next_midnight_toronto,
    today_toronto,
)
from db import (
    count_daily_players,
    create_daily_challenge,
    daily_leaderboard,
    get_daily_answers,
    get_daily_challenge,
    get_daily_result,
    get_daily_set_row,
    get_db,
    get_or_create_daily_set,
    get_quote,
    has_complete_daily_result,
    new_challenge_code,
    quote_play_view,
    quote_reveal_view,
    record_daily_answer,
    upsert_daily_result,
)
from moderation import validate_pseudo
from schemas import DailyAnswerIn, DailyChallengeCreateIn, DailyResultIn

router = APIRouter(prefix="/api/music-refs/daily", tags=["daily"])

# Tolérance (ms) entre le temps déclaré par le client et l'écart mesuré serveur
# entre la première et la dernière réponse (horloges différentes, latence).
TIME_SPAN_TOLERANCE_MS = 2000

MSG_REVEAL_FORBIDDEN = "Les réponses ne sont accessibles qu'après avoir joué les 5 citations du jour"
MSG_NO_ANSWERS = "Aucune réponse vérifiée par le serveur pour ce joueur : joue d'abord les citations du jour"
MSG_TIME_TOO_SHORT = "Temps trop court — score rejeté"
MSG_TIME_INCONSISTENT = "Temps incohérent avec les réponses enregistrées — score rejeté"
MSG_SCORE_INCONSISTENT = "Score incohérent avec les réponses vérifiées par le serveur"
MSG_CHALLENGE_NEEDS_RESULT = "Termine d'abord le set du jour avant de lancer un défi"


def _parse_day(raw: str | None) -> date:
    if not raw:
        return today_toronto()
    try:
        return date.fromisoformat(raw)
    except ValueError as e:
        raise HTTPException(400, "date invalide (YYYY-MM-DD)") from e


def _pseudo_or_422(raw: str | None) -> str:
    try:
        return validate_pseudo(raw)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


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
    day = _parse_day(date_str)
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
                view = quote_play_view(q)
                view["multiplier"] = rarity_multiplier(view["rarity"])
                view["hint_cost"] = hint_cost(view["rarity"])
                quotes.append(view)

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
    """Vérifie une réponse côté serveur. Ne révèle JAMAIS artiste/titre : le
    joueur n'obtient que le verdict (artist_ok/title_ok) et les points. Les
    réponses sont dévoilées uniquement par POST /result (set complet) ou
    GET /reveal (résultat complet enregistré)."""
    day_iso = _parse_day(body.date).isoformat()
    cat_key = body.category_key or "all"
    with get_db() as conn:
        q = get_quote(conn, body.quote_id)
        if not q:
            raise HTTPException(404, "Citation introuvable")
        dset = get_daily_set_row(conn, day_iso, cat_key)
        if not dset:
            raise HTTPException(404, "Set du jour introuvable")
        if body.quote_id not in dset["quote_ids"]:
            raise HTTPException(400, "Cette citation n'est pas dans le set du jour")

        artist_in = "" if body.skip else body.artist.strip()
        title_in = "" if body.skip else body.title.strip()
        artist_ok = is_match(artist_in, q["artist"]) if artist_in else False
        title_ok = is_match(title_in, q["title"]) if title_in else False
        # single field may match either
        if artist_in and not title_in:
            if is_match(artist_in, q["title"]):
                title_ok = True
            if is_match(artist_in, q["artist"]):
                artist_ok = True

        rarity = (q.get("rarity") or "commune").lower()
        mult = rarity_multiplier(rarity)
        points = answer_points(artist_ok, title_ok, rarity)
        score_delta = answer_score(artist_ok, title_ok, rarity, body.hints_used)
        hints_used = body.hints_used
        already = False

        if body.player_id:
            stored, created = record_daily_answer(
                conn,
                day_iso=day_iso,
                category_key=cat_key,
                player_id=body.player_id,
                quote_id=body.quote_id,
                artist_ok=artist_ok,
                title_ok=title_ok,
                hints=body.hints_used,
                score=score_delta,
                skipped=body.skip or (not artist_in and not title_in),
                answered_at_ms=int(time.time() * 1000),
            )
            if not created:
                # Première réponse définitive : on renvoie le verdict stocké.
                already = True
                artist_ok, title_ok = stored["artist_ok"], stored["title_ok"]
                points = answer_points(artist_ok, title_ok, rarity)
                score_delta = stored["score"]
                hints_used = stored["hints"]

        full = artist_ok and title_ok
        return {
            "artist_ok": artist_ok,
            "title_ok": title_ok,
            "fully_correct": full,
            "points": points,
            "score_delta": score_delta,
            "hint_cost": hint_cost(rarity),
            "rarity": rarity,
            "multiplier": mult,
            "cell": grid_cell(full, rarity, hints_used),
            "already_answered": already,
            "tracked": bool(body.player_id),
        }


@router.post("/result")
def post_result(body: DailyResultIn):
    """Enregistre le résultat du jour. Le score, le nombre de bonnes réponses,
    les indices et la grille sont RECALCULÉS à partir des réponses vérifiées
    par POST /answer ; la valeur envoyée par le client ne sert qu'au contrôle."""
    day = _parse_day(body.date)
    day_iso = day.isoformat()
    pseudo = _pseudo_or_422(body.pseudo)

    ed = edition_number(day)
    with get_db() as conn:
        if body.category_key:
            cat_key = body.category_key
        else:
            cat_key, _, _ = _resolve_category(conn, body.category_id, None)

        dset = get_daily_set_row(conn, day_iso, cat_key)
        if not dset:
            raise HTTPException(404, "Set du jour introuvable")
        set_ids = set(dset["quote_ids"])
        set_size = len(dset["quote_ids"])

        answers = [a for a in get_daily_answers(conn, day_iso, cat_key, body.player_id) if a["quote_id"] in set_ids]
        played = len(answers)
        if played == 0:
            raise HTTPException(400, MSG_NO_ANSWERS)

        # MR-13 anti-triche : temps minimal par citation…
        if body.time_ms < played * MIN_MS_PER_QUOTE:
            raise HTTPException(400, MSG_TIME_TOO_SHORT)
        # …et cohérence avec l'écart réel mesuré côté serveur
        span = answers[-1]["answered_at_ms"] - answers[0]["answered_at_ms"]
        if body.time_ms + TIME_SPAN_TOLERANCE_MS < span:
            raise HTTPException(400, MSG_TIME_INCONSISTENT)

        # Score serveur (autoritaire)
        server_score = sum(a["score"] for a in answers)
        server_correct = sum(1 for a in answers if a["artist_ok"] and a["title_ok"])
        server_hints = sum(a["hints"] for a in answers)
        if body.score > server_score or body.correct > server_correct:
            raise HTTPException(400, MSG_SCORE_INCONSISTENT)

        by_id = {a["quote_id"]: a for a in answers}
        cells = []
        for qid in dset["quote_ids"]:
            a = by_id.get(qid)
            if not a:
                continue
            q = get_quote(conn, qid)
            rarity = (q or {}).get("rarity") or "commune"
            cells.append(grid_cell(a["artist_ok"] and a["title_ok"], rarity, a["hints"]))
        grid = "".join(cells)

        complete = played >= set_size
        upsert_daily_result(
            conn,
            day_iso=day_iso,
            category_key=cat_key,
            edition=ed,
            player_id=body.player_id,
            pseudo=pseudo,
            score=server_score,
            correct=server_correct,
            hints=server_hints,
            time_ms=body.time_ms,
            grid=grid,
            played=played,
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

        # MR-04 / SEC-01 : réponses dévoilées seulement si le set est complet
        reveals: list[dict] = _reveals_for_set(conn, dset["quote_ids"]) if complete else []

    return {
        "ok": True,
        "complete": complete,
        "played": played,
        "score": server_score,
        "correct": server_correct,
        "hints": server_hints,
        "grid": grid,
        "pseudo": pseudo,
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
    day = _parse_day(date_str)
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
    player_id: str | None = Query(default=None, min_length=8, max_length=64),
    category_id: int | None = Query(default=None),
    category: str | None = Query(default=None),
    date_str: str | None = Query(default=None, alias="date"),
    category_key: str | None = Query(default=None),
):
    """Révélation artiste/titre/listen_url — réservée à un joueur ayant un
    résultat COMPLET (toutes les citations jouées) enregistré pour ce jour/catégorie."""
    day = _parse_day(date_str)
    day_iso = day.isoformat()
    if not player_id:
        raise HTTPException(403, MSG_REVEAL_FORBIDDEN)
    with get_db() as conn:
        if category_key:
            cat_key = category_key
        else:
            cat_key, _, _ = _resolve_category(conn, category_id, category)
        dset = get_daily_set_row(conn, day_iso, cat_key)
        if not dset:
            raise HTTPException(404, "Set du jour introuvable")
        if not has_complete_daily_result(conn, day_iso, cat_key, player_id):
            raise HTTPException(403, MSG_REVEAL_FORBIDDEN)
        return {
            "date": day_iso,
            "category_key": cat_key,
            "edition": dset["edition"],
            "reveals": _reveals_for_set(conn, dset["quote_ids"]),
        }


@router.post("/challenge")
def post_challenge(body: DailyChallengeCreateIn):
    day = _parse_day(body.date)
    day_iso = day.isoformat()
    pseudo = _pseudo_or_422(body.pseudo)
    with get_db() as conn:
        if body.category_key:
            cat_key = body.category_key
            cat_id = body.category_id
        else:
            cat_key, cat_id, _ = _resolve_category(conn, body.category_id, None)
        # Le défi reprend le résultat vérifié serveur, pas les valeurs envoyées.
        res = get_daily_result(conn, day_iso, cat_key, body.player_id)
        if not res or not has_complete_daily_result(conn, day_iso, cat_key, body.player_id):
            raise HTTPException(400, MSG_CHALLENGE_NEEDS_RESULT)
        code = new_challenge_code(conn)
        ch = create_daily_challenge(
            conn,
            code=code,
            day_iso=day_iso,
            category_key=cat_key,
            category_id=cat_id,
            creator_player_id=body.player_id,
            creator_pseudo=pseudo or res["pseudo"],
            creator_score=res["score"],
            creator_correct=res["correct"],
            creator_grid=res["grid"] or body.grid,
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
