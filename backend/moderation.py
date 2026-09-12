"""MR-12 — Filtre de pseudo côté serveur (mots interdits FR/EN).

Règles :
- Pseudo vide/absent → accepté (affiché « Anonyme »).
- Longueur 3–16 caractères après trim.
- Comparaison normalisée : minuscules, accents retirés, substitutions leet
  basiques (0→o 1→i 3→e 4→a 5→s 7→t @→a $→s), ponctuation/espaces retirés.
- Mots ≥ 4 lettres : détection en sous-chaîne ; mots plus courts : mot entier.
- Faux positifs : les radicaux légitimes de SAFE_STEMS (« dominique »,
  « depute », « analy »…) sont retirés de la forme compacte avant la recherche
  en sous-chaîne ; quelques mots trop ambigus (« bite » dans « habiter »,
  « rape » dans « grape »…) sont forcés en mot entier via WHOLE_WORD_ONLY.
"""

from __future__ import annotations

import re
import unicodedata

PSEUDO_MIN = 3
PSEUDO_MAX = 16

MSG_FORBIDDEN = "Ce pseudo n'est pas autorisé"
MSG_LENGTH = f"Le pseudo doit contenir entre {PSEUDO_MIN} et {PSEUDO_MAX} caractères"

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})

# Liste courte mais réaliste — insultes, slurs, sexuel explicite (FR/EN).
FORBIDDEN_WORDS: frozenset[str] = frozenset(
    {
        # FR — insultes
        "connard", "connasse", "conard", "salope", "salaud", "salop", "batard", "encule",
        "enculer", "enculé", "enfoire", "enfoiré", "putain", "pute", "putes", "merde",
        "merdeux", "trouduc", "ducon", "fdp", "ntm", "nique", "niquer", "niquetamere",
        "tg", "con", "conne", "abruti", "debile", "pd", "pede", "pedé", "tapette", "tarlouze",
        "gouine", "fiotte",
        # FR — slurs racistes
        "bougnoule", "youpin", "chinetoque", "bamboula", "negre", "negro", "bicot", "raton",
        "nazi", "hitler",
        # FR — sexuel explicite
        "bite", "teub", "zboub", "couille", "couilles", "chatte", "cul", "sexe", "suce",
        "sucer", "branle", "branlette", "fellation", "sodomie", "sperme", "vagin", "penis",
        "porno",
        # EN — insultes / slurs
        "fuck", "fucker", "fucking", "shit", "bitch", "asshole", "bastard", "cunt", "whore",
        "slut", "nigger", "nigga", "faggot", "fag", "retarded", "kkk", "ass",
        # EN — sexuel explicite
        "porn", "pussy", "dick", "cock", "cum", "anal", "rape", "rapist", "hentai", "sex",
        "tits", "tit", "boobs", "xxx", "nudes",
    }
)

# Mots ≥ 4 lettres trop ambigus en sous-chaîne → mot entier uniquement.
WHOLE_WORD_ONLY: frozenset[str] = frozenset(
    {
        "bite", "anal", "rape", "dick", "cock", "chatte", "suce", "sucer", "sexe", "conne",
        "raton", "bicot", "branle", "salop", "tits", "negro", "nudes",
    }
)

# Radicaux légitimes contenant un mot interdit : retirés de la forme compacte
# avant la détection en sous-chaîne (prénoms et mots courants).
SAFE_STEMS: tuple[str, ...] = (
    "dominique", "monique", "veronique", "angelique", "frederique", "unique",
    "depute", "repute", "ampute", "impute", "dispute", "compute",
    "bipede", "quadrupede", "centipede", "millipede", "velocipede", "pedestr", "stampede",
)


def _fold(s: str) -> str:
    """Minuscules, accents retirés, leet remplacé ; conserve les séparateurs."""
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.translate(LEET)


def _tokens(folded: str) -> list[str]:
    return [t for t in re.split(r"[^a-z]+", folded) if t]


def normalize_pseudo(s: str) -> str:
    """Forme compacte (lettres seulement) utilisée pour la détection en sous-chaîne."""
    return re.sub(r"[^a-z]+", "", _fold(s))


def _prepared_words() -> list[tuple[str, bool]]:
    out: list[tuple[str, bool]] = []
    for w in FORBIDDEN_WORDS:
        nw = normalize_pseudo(w)
        if not nw:
            continue
        substring = len(nw) >= 4 and w not in WHOLE_WORD_ONLY
        out.append((nw, substring))
    return sorted(out)


_WORDS = _prepared_words()


def _strip_safe_stems(compact: str) -> str:
    for stem in SAFE_STEMS:
        compact = compact.replace(stem, "")
    return compact


def find_forbidden(pseudo: str) -> str | None:
    """Retourne le mot interdit détecté (normalisé), ou None."""
    folded = _fold(pseudo)
    compact = re.sub(r"[^a-z]+", "", folded)
    tokens = set(_tokens(folded))
    if not compact:
        return None
    searchable = _strip_safe_stems(compact)
    for word, substring in _WORDS:
        if substring:
            if word in searchable:
                return word
        elif word in tokens or word == compact:
            return word
    return None


def is_pseudo_allowed(pseudo: str) -> bool:
    return find_forbidden(pseudo) is None


def validate_pseudo(pseudo: str | None) -> str:
    """Retourne le pseudo nettoyé ("" si absent) ou lève ValueError(message FR)."""
    cleaned = (pseudo or "").strip()
    if not cleaned:
        return ""
    if len(cleaned) < PSEUDO_MIN or len(cleaned) > PSEUDO_MAX:
        raise ValueError(MSG_LENGTH)
    if find_forbidden(cleaned):
        raise ValueError(MSG_FORBIDDEN)
    return cleaned
