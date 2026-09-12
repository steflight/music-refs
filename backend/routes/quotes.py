import random

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from auth import require_admin
from config import get_settings
from daily import normalize_answer
from db import (
    delete_quote,
    get_db,
    get_quote,
    insert_quote,
    list_quotes,
    random_quote,
    set_quote_categories,
    update_quote,
)
from providers import itunes, lrclib, musicbrainz
from schemas import (
    Hints,
    ImportRequest,
    ImportResponse,
    LyricsLine,
    QuoteCategoriesSet,
    QuoteAnswerIn,
    QuoteAnswerOut,
    QuoteCreate,
    QuoteOptionsOut,
    QuoteOut,
    QuotePublicOut,
    QuoteReveal,
    QuoteUpdate,
    QuotesBulkCreate,
)
from scoring import public_view, verdict

router = APIRouter(prefix="/api/music-refs", tags=["music-refs"])


def _initials(artist: str, title: str) -> str:
    def parts(s: str) -> str:
        tokens = [t for t in s.replace("-", " ").split() if t]
        return " ".join(f"{t[0].upper()}..." for t in tokens) if tokens else "..."

    return f"Artiste: {parts(artist)} / Titre: {parts(title)}"


def _to_out(data: dict) -> QuoteOut:
    return QuoteOut(**{**data, "category_ids": data.get("category_ids") or []})


def _to_public(data: dict) -> QuotePublicOut:
    return QuotePublicOut(**public_view(data))


def is_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> bool:
    """Admin optionnel : vrai seulement si le token est présent ET valide (SEC-01)."""
    return bool(x_admin_token) and x_admin_token == get_settings().admin_token


@router.get("/quotes", response_model=list[QuoteOut] | list[QuotePublicOut])
def get_quotes(
    category_id: int | None = Query(default=None),
    admin: bool = Depends(is_admin),
):
    """Catalogue. Sans `X-Admin-Token` valide : ni artiste, ni titre, ni lien d'écoute."""
    with get_db() as conn:
        rows = list_quotes(conn, category_id)
    if admin:
        return [_to_out(q) for q in rows]
    return [_to_public(q) for q in rows]


@router.get("/random", response_model=QuoteOut | QuotePublicOut)
def get_random(category_id: int | None = Query(default=None), admin: bool = Depends(is_admin)):
    with get_db() as conn:
        q = random_quote(conn, category_id)
    if not q:
        raise HTTPException(status_code=404, detail="No quotes in database")
    return _to_out(q) if admin else _to_public(q)


@router.get("/quotes/{quote_id}", response_model=QuoteOut | QuotePublicOut)
def get_one(quote_id: int, admin: bool = Depends(is_admin)):
    with get_db() as conn:
        q = get_quote(conn, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _to_out(q) if admin else _to_public(q)


_FILLERS = {
    "artist": ["Artiste Mystère", "Inconnu·e", "Anonymous", "DJ X"],
    "title": ["Sans titre", "Track #1", "Bonus", "Interlude"],
}


def build_options(quote: dict, pool: list[dict], count: int = 4) -> dict[str, list[str]]:
    """Choix multiples mélangés : la bonne réponse + distracteurs, sans indiquer laquelle est bonne."""
    others = [q for q in pool if q.get("id") != quote["id"]]

    def pick(field: str) -> list[str]:
        correct = (quote.get(field) or "").strip()
        seen = {normalize_answer(correct)}
        options = [correct]
        shuffled = list(others)
        random.shuffle(shuffled)
        for q in shuffled:
            val = (q.get(field) or "").strip()
            if not val:
                continue
            key = normalize_answer(val)
            if key in seen:
                continue
            seen.add(key)
            options.append(val)
            if len(options) >= count:
                break
        for f in _FILLERS[field]:
            if len(options) >= count:
                break
            key = normalize_answer(f)
            if key in seen:
                continue
            seen.add(key)
            options.append(f)
        random.shuffle(options)
        return options

    return {"artists": pick("artist"), "titles": pick("title")}


@router.get("/quotes/{quote_id}/options", response_model=QuoteOptionsOut)
def get_options(
    quote_id: int,
    count: int = Query(default=4, ge=2, le=8),
    category_id: int | None = Query(default=None, description="Pool des distracteurs"),
) -> QuoteOptionsOut:
    """SEC-01 — propositions du mode quiz (bonne réponse + distracteurs, mélangés)."""
    with get_db() as conn:
        q = get_quote(conn, quote_id)
        if not q:
            raise HTTPException(status_code=404, detail="Quote not found")
        pool_cat = category_id
        if pool_cat is None and q.get("category_ids"):
            pool_cat = q["category_ids"][0]
        pool = list_quotes(conn, pool_cat)
        if len(pool) < count:
            pool = list_quotes(conn, None)
    return QuoteOptionsOut(**build_options(q, pool, count))


@router.post("/quotes/{quote_id}/answer", response_model=QuoteAnswerOut)
def post_answer(quote_id: int, body: QuoteAnswerIn) -> QuoteAnswerOut:
    """SEC-02 — verdict serveur (MR-11). `points` = total cumulé pour l'état de la punchline."""
    if not body.artist.strip() and not body.title.strip():
        raise HTTPException(status_code=400, detail="Saisissez au moins l'artiste ou le titre.")
    with get_db() as conn:
        q = get_quote(conn, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteAnswerOut(**verdict(q, body.artist, body.title, body.hints_used))


@router.post("/quotes/{quote_id}/reveal", response_model=QuoteReveal)
def post_reveal(quote_id: int) -> QuoteReveal:
    """Abandon (« Passer ») : révèle la réponse d'UNE punchline, explicitement."""
    with get_db() as conn:
        q = get_quote(conn, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return QuoteReveal(artist=q["artist"], title=q["title"], listen_url=q.get("listen_url") or "")


@router.put("/quotes/{quote_id}/categories", response_model=QuoteOut, dependencies=[Depends(require_admin)])
def put_quote_categories(quote_id: int, body: QuoteCategoriesSet) -> QuoteOut:
    with get_db() as conn:
        q = set_quote_categories(conn, quote_id, body.category_ids)
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _to_out(q)


@router.post("/import", response_model=ImportResponse, dependencies=[Depends(require_admin)])
async def import_track(body: ImportRequest) -> ImportResponse:
    track = await lrclib.get_best_lyrics(body.artist, body.title)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lyrics found for {body.artist} — {body.title}",
        )

    meta = await itunes.lookup_metadata(
        track.get("artistName") or body.artist,
        track.get("trackName") or body.title,
    )
    if not meta.get("year") and not meta.get("album"):
        mb = await musicbrainz.lookup_metadata(
            track.get("artistName") or body.artist,
            track.get("trackName") or body.title,
        )
        meta = {
            "year": meta.get("year") or mb.get("year") or "",
            "genre": meta.get("genre") or mb.get("genre") or "",
            "album": meta.get("album") or mb.get("album") or "",
        }
    album = track.get("albumName") or meta.get("album") or ""
    artist = track.get("artistName") or body.artist
    title = track.get("trackName") or body.title
    hints = Hints(
        year=meta.get("year") or "",
        genre=meta.get("genre") or "",
        album=album,
        initials=_initials(artist, title),
    )
    lines = [LyricsLine(**line) for line in track.get("lyrics_lines") or []]
    return ImportResponse(
        track={
            "id": track.get("id"),
            "trackName": title,
            "artistName": artist,
            "albumName": album,
            "duration": track.get("duration"),
            "instrumental": track.get("instrumental", False),
        },
        lyrics_lines=lines,
        hints=hints,
    )


@router.post("/quotes", response_model=list[QuoteOut], dependencies=[Depends(require_admin)])
def create_quotes(body: QuotesBulkCreate) -> list[QuoteOut]:
    created: list[QuoteOut] = []
    with get_db() as conn:
        for item in body.quotes:
            hints = item.hints or Hints()
            if not hints.initials:
                hints.initials = _initials(item.artist, item.title)
            q = insert_quote(
                conn,
                quote=item.quote,
                artist=item.artist,
                title=item.title,
                year=hints.year,
                genre=hints.genre,
                album=hints.album,
                initials=hints.initials,
                listen_url=item.listen_url or "",
                rarity=item.rarity or "commune",
                category_ids=item.category_ids or None,
            )
            created.append(_to_out(q))
    return created


@router.post("/quotes/one", response_model=QuoteOut, dependencies=[Depends(require_admin)])
def create_one_quote(body: QuoteCreate) -> QuoteOut:
    hints = body.hints or Hints()
    if not hints.initials:
        hints.initials = _initials(body.artist, body.title)
    with get_db() as conn:
        q = insert_quote(
            conn,
            quote=body.quote,
            artist=body.artist,
            title=body.title,
            year=hints.year,
            genre=hints.genre,
            album=hints.album,
            initials=hints.initials,
            listen_url=body.listen_url or "",
            rarity=body.rarity or "commune",
            category_ids=body.category_ids or None,
        )
    return _to_out(q)


@router.patch("/quotes/{quote_id}", response_model=QuoteOut, dependencies=[Depends(require_admin)])
def patch_quote(quote_id: int, body: QuoteUpdate) -> QuoteOut:
    with get_db() as conn:
        q = update_quote(
            conn,
            quote_id,
            listen_url=body.listen_url,
            rarity=body.rarity,
            artist=body.artist,
            title=body.title,
            quote=body.quote,
        )
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _to_out(q)


@router.delete("/quotes/{quote_id}", dependencies=[Depends(require_admin)])
def remove_quote(quote_id: int) -> dict:
    with get_db() as conn:
        ok = delete_quote(conn, quote_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Quote not found")
    return {"ok": True, "deleted": quote_id}
