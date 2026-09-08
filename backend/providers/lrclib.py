"""LRCLIB lyrics provider — https://lrclib.net/docs"""

from __future__ import annotations

import re
from typing import Any

import httpx

from config import get_settings

LRCLIB_BASE = "https://lrclib.net"


def _headers() -> dict[str, str]:
    return {"User-Agent": get_settings().user_agent}


def _split_lyrics(plain: str | None) -> list[dict[str, Any]]:
    if not plain:
        return []
    lines: list[dict[str, Any]] = []
    for i, raw in enumerate(plain.splitlines()):
        text = raw.strip()
        if not text:
            continue
        # Skip section markers / credits noise
        if re.match(r"^\[.+\]$", text):
            continue
        if re.search(r"(?i)^(written by|lyrics by|composed by|copyright|©)", text):
            continue
        if len(text) < 8:
            continue
        lines.append({"index": i, "text": text, "candidate": len(text) >= 20})
    return lines


async def search_tracks(artist: str, title: str, limit: int = 8) -> list[dict[str, Any]]:
    q = f"{artist} {title}".strip()
    params = {"q": q}
    async with httpx.AsyncClient(timeout=20.0, headers=_headers()) as client:
        res = await client.get(f"{LRCLIB_BASE}/api/search", params=params)
        res.raise_for_status()
        results = res.json()
    out: list[dict[str, Any]] = []
    for item in results[:limit]:
        out.append(
            {
                "id": item.get("id"),
                "trackName": item.get("trackName") or item.get("name") or "",
                "artistName": item.get("artistName") or "",
                "albumName": item.get("albumName") or "",
                "duration": item.get("duration"),
                "instrumental": bool(item.get("instrumental")),
                "plainLyrics": item.get("plainLyrics"),
            }
        )
    return out


async def get_best_lyrics(artist: str, title: str) -> dict[str, Any] | None:
    """Return best matching track with plain lyrics lines."""
    results = await search_tracks(artist, title)
    if not results:
        # Try structured get
        async with httpx.AsyncClient(timeout=20.0, headers=_headers()) as client:
            res = await client.get(
                f"{LRCLIB_BASE}/api/get",
                params={
                    "artist_name": artist,
                    "track_name": title,
                    "album_name": "",
                    "duration": 0,
                },
            )
            if res.status_code == 404:
                return None
            if res.status_code >= 400:
                res.raise_for_status()
            item = res.json()
            results = [
                {
                    "id": item.get("id"),
                    "trackName": item.get("trackName") or title,
                    "artistName": item.get("artistName") or artist,
                    "albumName": item.get("albumName") or "",
                    "duration": item.get("duration"),
                    "instrumental": bool(item.get("instrumental")),
                    "plainLyrics": item.get("plainLyrics"),
                }
            ]

    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (s or "").lower())

    artist_n = _norm(artist)
    title_n = _norm(title)
    ranked = sorted(
        results,
        key=lambda t: (
            0 if _norm(t.get("artistName") or "") == artist_n else 1,
            0 if _norm(t.get("trackName") or "") == title_n else 1,
            0 if title_n and title_n in _norm(t.get("trackName") or "") else 1,
            0 if t.get("plainLyrics") else 1,
            # Prefer shorter track names (Macarena over Θ. Macarena (Paused))
            len(t.get("trackName") or ""),
        ),
    )
    best = ranked[0] if ranked else None
    if not best:
        return None
    if not best.get("plainLyrics") and best.get("id"):
        async with httpx.AsyncClient(timeout=20.0, headers=_headers()) as client:
            res = await client.get(f"{LRCLIB_BASE}/api/get/{best['id']}")
            if res.status_code == 200:
                detail = res.json()
                best["plainLyrics"] = detail.get("plainLyrics")
                best["albumName"] = best.get("albumName") or detail.get("albumName") or ""

    lines = _split_lyrics(best.get("plainLyrics"))
    return {
        "id": best.get("id"),
        "trackName": best.get("trackName") or title,
        "artistName": best.get("artistName") or artist,
        "albumName": best.get("albumName") or "",
        "duration": best.get("duration"),
        "instrumental": best.get("instrumental", False),
        "lyrics_lines": lines,
    }
