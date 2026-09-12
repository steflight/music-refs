"""Daily Refs — deterministic set selection (America/Toronto)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Toronto")
LAUNCH_DATE = date(2026, 9, 10)  # edition #1
LOOKBACK_DAYS = 90
SET_SIZE = 5

RARITY_MULT = {
    "commune": 1.0,
    "rare": 1.5,
    "legendaire": 2.0,
}

_ARTICLE_RE = re.compile(
    r"^(?:l'|d'|le|la|les|un|une|des|du|de|the|a|an)\s+",
    re.IGNORECASE,
)


def today_toronto() -> date:
    return datetime.now(TZ).date()


def edition_number(d: date) -> int:
    return max(1, (d - LAUNCH_DATE).days + 1)


def mulberry32(seed: int):
    state = seed & 0xFFFFFFFF

    def rand() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & 0xFFFFFFFF
        t = state
        t = (t ^ (t >> 15)) * (t | 1) & 0xFFFFFFFF
        t ^= t + ((t ^ (t >> 7)) * (t | 61) & 0xFFFFFFFF)
        t &= 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    return rand


def seed_int(day: date, category_key: str) -> int:
    raw = f"{day.isoformat()}|{category_key}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def strip_leading_articles(s: str) -> str:
    if not s:
        return ""
    out = s.strip()
    prev = None
    while prev != out:
        prev = out
        out = re.sub(r"^(l'|d')", "", out, flags=re.IGNORECASE)
        out = _ARTICLE_RE.sub("", out)
        out = out.strip()
    return out


def normalize_answer(s: str) -> str:
    if not s:
        return ""
    s = strip_leading_articles(s)
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def tokenize(s: str) -> list[str]:
    if not s:
        return []
    s = strip_leading_articles(s)
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("'", "").replace("'", "")
    return [t for t in re.split(r"[^a-z0-9]+", s) if t]


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def first_names_ok(a: str, b: str) -> bool:
    if not a or not b:
        return True
    if a == b:
        return True
    if len(a) == 1 and b.startswith(a):
        return True
    if len(b) == 1 and a.startswith(b):
        return True
    if len(a) >= 3 and len(b) >= 3 and (a.startswith(b) or b.startswith(a)):
        return True
    return levenshtein(a, b) <= 1


def is_match(input_s: str, target: str) -> bool:
    ni, nt = normalize_answer(input_s), normalize_answer(target)
    if not ni or not nt:
        return False
    if ni == nt:
        return True
    # aliases Pokora / Gims
    aliases = [
        {"mpokora", "mattpokora", "matthieupokora"},
        {"gims", "maitregims"},
        {"sexiondassaut", "sexiondassault"},
        {"belkatobis", "belkatobbi", "belkatobi"},
    ]
    for group in aliases:
        if ni in group and nt in group:
            return True
    if len(ni) >= 3 and (ni in nt or nt in ni):
        return True
    ti, tt = tokenize(input_s), tokenize(target)
    if ti and tt:
        if ti[-1] == tt[-1] and len(ti[-1]) >= 4:
            if len(ti) == 1 or len(tt) == 1 or first_names_ok(ti[0], tt[0]):
                return True
        if len(ti) <= len(tt) and all(
            any(
                x == tok
                or (len(tok) == 1 and x.startswith(tok))
                or (len(tok) >= 3 and x.startswith(tok))
                for x in tt
            )
            for tok in ti
        ):
            return True
    # Levenshtein ≤2 si cible ≥6 lettres, sinon ≤1
    max_d = 2 if len(nt) >= 6 else 1
    return levenshtein(ni, nt) <= max_d


def rarity_multiplier(rarity: str | None) -> float:
    key = (rarity or "commune").lower().strip()
    return RARITY_MULT.get(key, 1.0)


def _apply_rarity_constraints(candidates: list[dict[str, Any]], size: int) -> list[dict[str, Any]]:
    """≤1 légendaire, ≥1 commune (si le pool le permet)."""
    chosen: list[dict] = []
    legend_used = 0
    for q in candidates:
        if len(chosen) >= size:
            break
        rarity = (q.get("rarity") or "commune").lower()
        if rarity == "legendaire" and legend_used >= 1:
            continue
        chosen.append(q)
        if rarity == "legendaire":
            legend_used += 1

    # Garantir ≥1 commune si possible
    has_common = any((q.get("rarity") or "commune").lower() == "commune" for q in chosen)
    if not has_common and chosen:
        commons = [q for q in candidates if (q.get("rarity") or "commune").lower() == "commune"]
        if commons:
            # Remplacer le dernier non-commune
            for i in range(len(chosen) - 1, -1, -1):
                if (chosen[i].get("rarity") or "commune").lower() != "commune":
                    swap = next((c for c in commons if c not in chosen), None)
                    if swap:
                        chosen[i] = swap
                    break
            else:
                swap = next((c for c in commons if c not in chosen), None)
                if swap and len(chosen) < size:
                    chosen.append(swap)
                elif swap:
                    chosen[-1] = swap

    # Remplir si sous-effectif (pool trop filtré)
    if len(chosen) < size:
        for q in candidates:
            if len(chosen) >= size:
                break
            if q not in chosen:
                rarity = (q.get("rarity") or "commune").lower()
                if rarity == "legendaire" and sum(
                    1 for c in chosen if (c.get("rarity") or "").lower() == "legendaire"
                ) >= 1:
                    continue
                chosen.append(q)
    return chosen[:size]


def pick_quote_ids(
    pool: list[dict[str, Any]],
    day: date,
    category_key: str,
    recent_ids: set[int],
    size: int = SET_SIZE,
) -> list[int]:
    """pool items: {id, category_ids: list[int], rarity?: str}."""
    eligible = [q for q in pool if q["id"] not in recent_ids]
    if len(eligible) < size:
        eligible = list(pool)
    eligible = sorted(eligible, key=lambda q: q["id"])
    rng = mulberry32(seed_int(day, category_key))
    arr = list(eligible)
    for i in range(len(arr) - 1, 0, -1):
        j = int(rng() * (i + 1))
        arr[i], arr[j] = arr[j], arr[i]

    if category_key != "all":
        return [q["id"] for q in _apply_rarity_constraints(arr, size)]

    chosen: list[dict] = []
    seen_cats: set[int] = set()
    # Pass 1: prefer new categories until 3 distinct
    for q in arr:
        if len(chosen) >= size:
            break
        cats = set(q.get("category_ids") or [])
        rarity = (q.get("rarity") or "commune").lower()
        if rarity == "legendaire" and any(
            (c.get("rarity") or "").lower() == "legendaire" for c in chosen
        ):
            continue
        if len(seen_cats) < 3 and cats and cats.isdisjoint(seen_cats):
            chosen.append(q)
            seen_cats |= cats
    # Pass 2: fill with rarity constraints
    for q in arr:
        if len(chosen) >= size:
            break
        if q in chosen:
            continue
        rarity = (q.get("rarity") or "commune").lower()
        if rarity == "legendaire" and any(
            (c.get("rarity") or "").lower() == "legendaire" for c in chosen
        ):
            continue
        chosen.append(q)
        seen_cats |= set(q.get("category_ids") or [])
    chosen = _apply_rarity_constraints(chosen + [q for q in arr if q not in chosen], size)
    return [q["id"] for q in chosen[:size]]


def seconds_until_next_midnight_toronto() -> int:
    now = datetime.now(TZ)
    nxt = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=TZ)
    return max(0, int((nxt - now).total_seconds()))
