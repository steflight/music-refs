"""Lot A — règles serveur du mode Refs du jour (MR-04/SEC-01, MR-09, MR-12, MR-13).

Lancer : cd backend && python3 -m pytest tests -q
Base SQLite temporaire via DATABASE_PATH (cf. backend/config.py).
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_TMP = tempfile.mkdtemp(prefix="mr-daily-rules-")
os.environ["DATABASE_PATH"] = str(Path(_TMP) / "quotes.db")

from config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

import daily as daily_mod  # noqa: E402
import moderation  # noqa: E402
from db import get_db, init_db, insert_quote  # noqa: E402
from main import app  # noqa: E402

DAY = "2026-09-11"
CAT = "all"

SEED = [
    ("J'ai pas le temps de regretter mes choix", "Ninho", "Jefe", "commune"),
    ("Le monde est à nous", "PNL", "A l'ammoniaque", "commune"),
    ("On est ensemble comme les doigts de la main", "Sexion d'Assaut", "Désolé", "commune"),
    ("Je suis un vrai de vrai", "Booba", "DKR", "commune"),
    ("La rue c'est pas un jeu", "Jul", "Tchikita", "rare"),
    ("Étoile filante dans la nuit", "Nekfeu", "On verra", "legendaire"),
]


@pytest.fixture(scope="module")
def client():
    # Sans `with` : pas d'événement startup (pas de seed massif) → seed minimal ici.
    init_db()
    with get_db() as conn:
        for quote, artist, title, rarity in SEED:
            insert_quote(conn, quote=quote, artist=artist, title=title, rarity=rarity)
    return TestClient(app)


def _pid() -> str:
    return "p-" + uuid.uuid4().hex[:20]


def _pack(client):
    r = client.get("/api/music-refs/daily", params={"date": DAY, "category": CAT})
    assert r.status_code == 200, r.text
    return r.json()


def _answer_for(quote_text: str) -> tuple[str, str, str]:
    for q, a, t, rar in SEED:
        if q == quote_text:
            return a, t, rar
    raise AssertionError(f"citation inconnue: {quote_text}")


def _play(client, pid: str, n: int | None = None, correct: bool = True, hints: int = 0):
    """Joue n citations (toutes par défaut) pour ce joueur ; renvoie (pack, réponses)."""
    pack = _pack(client)
    quotes = pack["quotes"][: n if n is not None else len(pack["quotes"])]
    out = []
    for q in quotes:
        artist, title, _ = _answer_for(q["quote"])
        payload = {
            "quote_id": q["id"],
            "artist": artist if correct else "zzz",
            "title": title if correct else "zzz",
            "date": DAY,
            "category_key": CAT,
            "player_id": pid,
            "hints_used": hints,
        }
        r = client.post("/api/music-refs/daily/answer", json=payload)
        assert r.status_code == 200, r.text
        out.append(r.json())
    return pack, out


def _result(client, pid: str, answers, **overrides):
    score = sum(a["score_delta"] for a in answers)
    correct = sum(1 for a in answers if a["fully_correct"])
    body = {
        "player_id": pid,
        "pseudo": "",
        "score": score,
        "correct": correct,
        "hints": 0,
        "time_ms": 60_000,
        "grid": "",
        "date": DAY,
        "category_key": CAT,
    }
    body.update(overrides)
    return client.post("/api/music-refs/daily/result", json=body)


# --- MR-04 / SEC-01 : révélation ---------------------------------------------


def test_reveal_refused_without_player_or_result(client):
    _pack(client)  # crée le set du jour
    r = client.get("/api/music-refs/daily/reveal", params={"date": DAY, "category_key": CAT})
    assert r.status_code == 403
    assert "citations" in r.json()["detail"]

    r = client.get(
        "/api/music-refs/daily/reveal",
        params={"date": DAY, "category_key": CAT, "player_id": _pid()},
    )
    assert r.status_code == 403
    body = r.text
    for _, artist, title, _ in SEED:
        assert artist not in body and title not in body


def test_reveal_refused_when_result_incomplete(client):
    pid = _pid()
    _, answers = _play(client, pid, n=3)
    r = _result(client, pid, answers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["complete"] is False and data["played"] == 3
    assert data["reveals"] == []
    r = client.get(
        "/api/music-refs/daily/reveal",
        params={"date": DAY, "category_key": CAT, "player_id": pid},
    )
    assert r.status_code == 403


def test_reveal_accepted_after_complete_result(client):
    pid = _pid()
    pack, answers = _play(client, pid)
    r = _result(client, pid, answers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["complete"] is True and data["played"] == len(pack["quotes"])
    assert len(data["reveals"]) == len(pack["quotes"])
    assert all(rv["artist"] and rv["title"] for rv in data["reveals"])

    r = client.get(
        "/api/music-refs/daily/reveal",
        params={"date": DAY, "category_key": CAT, "player_id": pid},
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["reveals"]) == len(pack["quotes"])


def test_answer_never_reveals_artist_or_title(client):
    pid = _pid()
    _, answers = _play(client, pid)
    for a in answers:
        assert a["fully_correct"] is True
        assert "reveal" not in a and "artist" not in a and "title" not in a
        text = str(a)
        for _, artist, title, _ in SEED:
            assert artist not in text and title not in text


def test_daily_play_view_has_no_answers(client):
    pack = _pack(client)
    for q in pack["quotes"]:
        assert "artist" not in q and "title" not in q and "listen_url" not in q
        assert q["multiplier"] == daily_mod.rarity_multiplier(q["rarity"])
        assert q["hint_cost"] == 20 * q["multiplier"]


# --- MR-09 : multiplicateurs de rareté --------------------------------------


def test_rarity_multipliers_and_hint_costs():
    assert daily_mod.rarity_multiplier("commune") == 1
    assert daily_mod.rarity_multiplier("rare") == 2
    assert daily_mod.rarity_multiplier("legendaire") == 3
    assert daily_mod.rarity_multiplier(None) == 1
    assert daily_mod.hint_cost("commune") == 20
    assert daily_mod.hint_cost("rare") == 40
    assert daily_mod.hint_cost("legendaire") == 60
    assert daily_mod.answer_points(True, True, "commune") == 250
    assert daily_mod.answer_points(True, True, "rare") == 500
    assert daily_mod.answer_points(True, True, "legendaire") == 750
    assert daily_mod.answer_points(True, False, "legendaire") == 300
    assert daily_mod.answer_score(True, True, "legendaire", hints_used=1) == 690
    assert daily_mod.answer_score(True, False, "rare", hints_used=0) == 0
    assert daily_mod.answer_score(True, True, "commune", hints_used=3) == 190


def test_answer_endpoint_applies_multiplier(client):
    pid = _pid()
    pack, answers = _play(client, pid, hints=1)
    by_rarity = {q["rarity"]: a for q, a in zip(pack["quotes"], answers)}
    assert "rare" in by_rarity or "legendaire" in by_rarity
    for rarity, a in by_rarity.items():
        mult = {"commune": 1, "rare": 2, "legendaire": 3}[rarity]
        assert a["multiplier"] == mult
        assert a["points"] == 250 * mult
        assert a["hint_cost"] == 20 * mult
        assert a["score_delta"] == 250 * mult - 20 * mult
        assert a["cell"] == ("🟪" if rarity == "legendaire" else "🟨")


def test_set_rarity_constraints():
    from datetime import date

    def mk(ids, rarity):
        return [{"id": i, "category_ids": [], "rarity": rarity} for i in ids]

    # Pool réaliste : la contrainte est satisfaisable sur plusieurs jours
    pool = mk(range(1, 4), "legendaire") + mk(range(4, 7), "rare") + mk(range(7, 12), "commune")
    for key in ("all", "cat:1"):
        for d in range(1, 15):
            ids = daily_mod.pick_quote_ids(pool, date(2026, 9, d), key, set(), size=5)
            rarities = [next(p["rarity"] for p in pool if p["id"] == i) for i in ids]
            assert len(ids) == 5 and len(set(ids)) == 5
            assert rarities.count("legendaire") <= 1
            assert rarities.count("commune") >= 1

    # Pool dégénéré (que des légendaires + 1 commune + 1 rare) : on garde un set
    # complet de 5 plutôt qu'un set tronqué (MR-01 « exactement 5 »).
    degenerate = mk(range(1, 8), "legendaire") + mk([8], "commune") + mk([9], "rare")
    ids = daily_mod.pick_quote_ids(degenerate, date(2026, 9, 11), "all", set(), size=5)
    assert len(ids) == 5 and 8 in ids


# --- MR-12 : filtre de pseudo ----------------------------------------------


@pytest.mark.parametrize(
    "pseudo",
    ["C0nnard", "S@lope", "fdp_", "Ni.que", "En-culé", "F U C K", "b1tch", "pu73", "Pédé", "n1gg4", "Sal0pe22", "xXPuteXx"],
)
def test_pseudo_rejected_variants(pseudo):
    assert moderation.is_pseudo_allowed(pseudo) is False
    with pytest.raises(ValueError) as e:
        moderation.validate_pseudo(pseudo)
    assert str(e.value) == moderation.MSG_FORBIDDEN


@pytest.mark.parametrize(
    "pseudo",
    ["Lex", "Dominique", "Monique", "Frédérique", "Analyste", "député42", "Titi", "Cumulus", "Karim_93", "Véro", "Sussex", "Habiter", "Bipède"],
)
def test_pseudo_accepted(pseudo):
    assert moderation.validate_pseudo(pseudo) == pseudo


def test_pseudo_length_and_empty():
    assert moderation.validate_pseudo("") == ""
    assert moderation.validate_pseudo(None) == ""
    assert moderation.validate_pseudo("   ") == ""
    for bad in ("ab", "a" * 17):
        with pytest.raises(ValueError) as e:
            moderation.validate_pseudo(bad)
        assert str(e.value) == moderation.MSG_LENGTH


def test_result_rejects_forbidden_pseudo_with_422(client):
    pid = _pid()
    _, answers = _play(client, pid)
    r = _result(client, pid, answers, pseudo="C0nn@rd")
    assert r.status_code == 422
    assert r.json()["detail"] == "Ce pseudo n'est pas autorisé"
    r = _result(client, pid, answers, pseudo="ab")
    assert r.status_code == 422
    assert "entre 3 et 16" in r.json()["detail"]
    # Pseudo vide → accepté, affiché « Anonyme »
    r = _result(client, pid, answers, pseudo="")
    assert r.status_code == 200, r.text
    assert r.json()["pseudo"] == ""
    # Pseudo correct → accepté et visible dans le classement
    r = _result(client, pid, answers, pseudo="Karim_93")
    assert r.status_code == 200, r.text
    assert any(row["pseudo"] == "Karim_93" for row in r.json()["leaderboard"])


def test_challenge_rejects_forbidden_pseudo_and_uses_server_result(client):
    pid = _pid()
    _, answers = _play(client, pid)
    assert _result(client, pid, answers, pseudo="Lex").status_code == 200
    base = {
        "player_id": pid,
        "score": 999,
        "correct": 5,
        "grid": "",
        "date": DAY,
        "category_key": CAT,
    }
    r = client.post("/api/music-refs/daily/challenge", json={**base, "pseudo": "S@l0pe"})
    assert r.status_code == 422
    assert r.json()["detail"] == "Ce pseudo n'est pas autorisé"
    r = client.post("/api/music-refs/daily/challenge", json={**base, "pseudo": "Lex"})
    assert r.status_code == 200, r.text
    ch = r.json()["challenge"]
    assert ch["creator_score"] == sum(a["score_delta"] for a in answers)  # pas 999
    assert ch["creator_pseudo"] == "Lex"

    # Sans résultat complet : refusé
    r = client.post("/api/music-refs/daily/challenge", json={**base, "player_id": _pid(), "pseudo": "Lex"})
    assert r.status_code == 400


# --- MR-13 : anti-triche ----------------------------------------------------


def test_result_rejects_time_too_short(client):
    pid = _pid()
    _, answers = _play(client, pid)
    r = _result(client, pid, answers, time_ms=14_999)
    assert r.status_code == 400
    assert r.json()["detail"] == "Temps trop court — score rejeté"
    r = _result(client, pid, answers, time_ms=15_000)
    assert r.status_code == 200, r.text


def test_result_rejects_inflated_score_and_uses_server_values(client):
    pid = _pid()
    pack, answers = _play(client, pid, correct=False)
    server_score = sum(a["score_delta"] for a in answers)
    assert server_score == 0
    r = _result(client, pid, answers, score=1250, correct=5)
    assert r.status_code == 400
    assert "incohérent" in r.json()["detail"]
    r = _result(client, pid, answers, score=0, correct=0, grid="🟩🟩🟩🟩🟩")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["score"] == 0 and data["correct"] == 0
    assert data["grid"] == "⬛" * len(pack["quotes"])  # grille recalculée serveur


def test_result_rejects_without_server_answers(client):
    r = _result(client, _pid(), [], score=0, correct=0)
    assert r.status_code == 400
    assert "réponse vérifiée" in r.json()["detail"]


def test_first_answer_is_final(client):
    pid = _pid()
    pack = _pack(client)
    q = pack["quotes"][0]
    base = {"quote_id": q["id"], "date": DAY, "category_key": CAT, "player_id": pid}
    r1 = client.post("/api/music-refs/daily/answer", json={**base, "artist": "zzz", "title": "zzz"})
    assert r1.status_code == 200 and r1.json()["fully_correct"] is False
    artist, title, _ = _answer_for(q["quote"])
    r2 = client.post("/api/music-refs/daily/answer", json={**base, "artist": artist, "title": title})
    assert r2.status_code == 200
    assert r2.json()["already_answered"] is True
    assert r2.json()["fully_correct"] is False
    assert r2.json()["score_delta"] == 0
