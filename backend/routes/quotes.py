from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_admin
from db import (
    delete_quote,
    get_db,
    get_quote,
    insert_quote,
    list_quotes,
    random_quote,
    set_quote_categories,
)
from providers import itunes, lrclib, musicbrainz
from schemas import (
    Hints,
    ImportRequest,
    ImportResponse,
    LyricsLine,
    QuoteCategoriesSet,
    QuoteCreate,
    QuoteOut,
    QuotesBulkCreate,
)

router = APIRouter(prefix="/api/music-refs", tags=["music-refs"])


def _initials(artist: str, title: str) -> str:
    def parts(s: str) -> str:
        tokens = [t for t in s.replace("-", " ").split() if t]
        return " ".join(f"{t[0].upper()}..." for t in tokens) if tokens else "..."

    return f"Artiste: {parts(artist)} / Titre: {parts(title)}"


def _to_out(data: dict) -> QuoteOut:
    return QuoteOut(**{**data, "category_ids": data.get("category_ids") or []})


@router.get("/quotes", response_model=list[QuoteOut])
def get_quotes(category_id: int | None = Query(default=None)) -> list[QuoteOut]:
    with get_db() as conn:
        return [_to_out(q) for q in list_quotes(conn, category_id)]


@router.get("/random", response_model=QuoteOut)
def get_random(category_id: int | None = Query(default=None)) -> QuoteOut:
    with get_db() as conn:
        q = random_quote(conn, category_id)
    if not q:
        raise HTTPException(status_code=404, detail="No quotes in database")
    return _to_out(q)


@router.get("/quotes/{quote_id}", response_model=QuoteOut)
def get_one(quote_id: int) -> QuoteOut:
    with get_db() as conn:
        q = get_quote(conn, quote_id)
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _to_out(q)


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
            category_ids=body.category_ids or None,
        )
    return _to_out(q)


@router.delete("/quotes/{quote_id}", dependencies=[Depends(require_admin)])
def remove_quote(quote_id: int) -> dict:
    with get_db() as conn:
        ok = delete_quote(conn, quote_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Quote not found")
    return {"ok": True, "deleted": quote_id}
