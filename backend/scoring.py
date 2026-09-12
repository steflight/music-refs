"""SEC-02 / SEC-03 — Verdict et barème calculés côté serveur (règle MR-11).

Réutilise `daily.is_match` (casse, accents, articles, alias, Levenshtein ≤ 2
pour les cibles ≥ 6 lettres).

Barème (identique à l'ancien moteur local du mode solo) :
- artiste trouvé : 100 ; titre trouvé : 100 ; les deux : +50 de bonus ;
- « artiste juste mais titre faux » = 100/200 → moitié des points (MR-11) ;
- indices : −20 par indice utilisé (max 4), plancher 20 dès qu'un champ est juste ;
- multiplicateur de rareté (MR-09) appliqué en dernier.

`points` est CUMULATIF pour l'état de la punchline (le client renvoie l'artiste
déjà validé avec le nouveau titre) ; le client calcule le delta à ajouter.
"""

from __future__ import annotations

from typing import Any

from daily import is_match, rarity_multiplier

POINTS_FIELD = 100
BONUS_FULL = 50
HINT_PENALTY = 20
MAX_HINTS = 4
MIN_POINTS = 20


def check_answer(quote: dict[str, Any], artist: str, title: str) -> tuple[bool, bool]:
    artist = (artist or "").strip()
    title = (title or "").strip()
    artist_ok = is_match(artist, quote["artist"]) if artist else False
    title_ok = is_match(title, quote["title"]) if title else False
    # Un seul champ saisi : il peut désigner l'un ou l'autre.
    if artist and not title:
        if is_match(artist, quote["title"]):
            title_ok = True
    if title and not artist:
        if is_match(title, quote["artist"]):
            artist_ok = True
    return artist_ok, title_ok


def compute_points(artist_ok: bool, title_ok: bool, hints_used: int, rarity: str | None) -> tuple[int, float]:
    base = 0
    if artist_ok:
        base += POINTS_FIELD
    if title_ok:
        base += POINTS_FIELD
    if artist_ok and title_ok:
        base += BONUS_FULL
    if base <= 0:
        return 0, rarity_multiplier(rarity)
    penalty = max(0, min(int(hints_used or 0), MAX_HINTS)) * HINT_PENALTY
    base = max(MIN_POINTS, base - penalty)
    mult = rarity_multiplier(rarity)
    return int(round(base * mult)), mult


def verdict(quote: dict[str, Any], artist: str, title: str, hints_used: int = 0) -> dict[str, Any]:
    artist_ok, title_ok = check_answer(quote, artist, title)
    rarity = (quote.get("rarity") or "commune").lower()
    points, mult = compute_points(artist_ok, title_ok, hints_used, rarity)
    fully = artist_ok and title_ok
    half = artist_ok and not title_ok
    if fully:
        message = f"Artiste trouvé: {quote['artist']} | Titre trouvé: {quote['title']}"
    elif half:
        message = f"Artiste juste ({quote['artist']}), titre faux : moitié des points."
    elif title_ok:
        message = f"Titre trouvé: {quote['title']} — il manque l'artiste."
    else:
        message = "Mauvaise réponse. Réessayez ou demandez un indice !"
    reveal = None
    if fully:
        reveal = {
            "artist": quote["artist"],
            "title": quote["title"],
            "listen_url": quote.get("listen_url") or "",
        }
    return {
        "artist_ok": artist_ok,
        "title_ok": title_ok,
        "fully_correct": fully,
        "points": points,
        "half_points": half,
        "rarity": rarity,
        "multiplier": mult,
        "message": message,
        "reveal": reveal,
    }


def public_view(q: dict[str, Any]) -> dict[str, Any]:
    """Punchline sans artiste, titre ni lien d'écoute (SEC-01)."""
    hints = q.get("hints") or {}
    rarity = (q.get("rarity") or "commune").lower()
    if rarity not in {"commune", "rare", "legendaire"}:
        rarity = "commune"
    return {
        "id": q["id"],
        "quote": q["quote"],
        "rarity": rarity,
        "hints": {
            "year": hints.get("year") or "",
            "genre": hints.get("genre") or "",
            "album": hints.get("album") or "",
            "initials": hints.get("initials") or "",
        },
        "category_ids": q.get("category_ids") or [],
    }
