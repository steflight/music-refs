"""MusicBrainz metadata fallback (no API key; polite User-Agent required)."""

from __future__ import annotations

from urllib.parse import quote

import httpx

from config import get_settings

MB_BASE = "https://musicbrainz.org/ws/2"


async def lookup_metadata(artist: str, title: str) -> dict[str, str]:
    query = f'artist:"{artist}" AND recording:"{title}"'
    url = f"{MB_BASE}/recording/?query={quote(query)}&fmt=json&limit=5"
    headers = {"User-Agent": get_settings().user_agent, "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
        res = await client.get(url)
        if res.status_code >= 400:
            return {"year": "", "genre": "", "album": ""}
        payload = res.json()

    recordings = payload.get("recordings") or []
    if not recordings:
        return {"year": "", "genre": "", "album": ""}

    best = recordings[0]
    year = ""
    if best.get("first-release-date"):
        year = str(best["first-release-date"])[:4]
    album = ""
    releases = best.get("releases") or []
    if releases:
        album = releases[0].get("title") or ""
    tags = best.get("tags") or []
    genre = tags[0].get("name", "") if tags else ""
    return {"year": year, "genre": genre, "album": album}
