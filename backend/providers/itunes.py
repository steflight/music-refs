"""iTunes Search API for track metadata (no API key)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import httpx

from config import get_settings


async def lookup_metadata(artist: str, title: str) -> dict[str, str]:
    term = quote_plus(f"{artist} {title}")
    url = f"https://itunes.apple.com/search?term={term}&media=music&entity=song&limit=10"
    headers = {"User-Agent": get_settings().user_agent}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        res = await client.get(url)
        res.raise_for_status()
        payload = res.json()

    results = payload.get("results") or []
    if not results:
        return {"year": "", "genre": "", "album": ""}

    artist_l = artist.lower().strip()
    title_l = title.lower().strip()

    # Keep only results whose artist name matches (avoid false positives)
    filtered = [
        t for t in results if artist_l in (t.get("artistName") or "").lower()
    ] or results

    ranked = sorted(
        filtered,
        key=lambda t: (
            0 if (t.get("artistName") or "").lower() == artist_l else 1,
            0 if title_l in (t.get("trackName") or "").lower() else 1,
        ),
    )
    best = ranked[0]
    # Reject if artist clearly wrong
    if artist_l not in (best.get("artistName") or "").lower():
        return {"year": "", "genre": "", "album": ""}

    release = best.get("releaseDate") or ""
    year = release[:4] if len(release) >= 4 else ""
    return {
        "year": year,
        "genre": best.get("primaryGenreName") or "",
        "album": best.get("collectionName") or "",
    }
