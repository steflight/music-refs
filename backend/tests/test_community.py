"""Lot F — contenu communautaire (MR-16 proposer une punchline, MR-17 vote).

Lancer : cd backend && python3 -m pytest tests -q
Base SQLite temporaire via DATABASE_PATH (cf. backend/config.py). Le rate-limit
global (SEC-04) est neutralisé pour ce module (`ratelimit.set_limit(0)`).
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from datetime import date
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from fastapi.testclient import TestClient  # noqa: E402

import ratelimit  # noqa: E402
from config import get_settings  # noqa: E402
from db import get_db, init_db, insert_quote  # noqa: E402
from main import app  # noqa: E402
from routes.community import SUBMISSIONS_PER_DAY, listen_url_allowed  # noqa: E402

# L'environnement (base temporaire, token) est posé dans la fixture de module et
# RESTAURÉ ensuite : rien n'est modifié à l'import, pour ne pas partager la base
# (ni le token) avec les autres modules de tests.
TOKEN = "community-test-token"
ADMIN = {"X-Admin-Token": TOKEN}
_ENV_KEYS = ("DATABASE_PATH", "ADMIN_TOKEN")
API = "/api/music-refs"
DAY = "2026-09-05"
CAT = "all"

SEED = [
    ("Le temps c'est de l'argent et j'ai pas de monnaie", "Damso", "Macarena"),
    ("Dans la légende on y est déjà", "PNL", "Dans la légende"),
    ("Je viens de loin, j'ai marché longtemps", "Kery James", "Banlieusards"),
    ("La vie est belle, le destin s'en écarte", "IAM", "Petit frère"),
    ("Ils ont voulu me voir tomber", "Booba", "Kalash"),
    ("Y a que la vérité qui blesse", "Orelsan", "La terre est ronde"),
]


@pytest.fixture(scope="module")
def client():
    saved = {k: os.environ.get(k) for k in _ENV_KEYS}
    tmp = tempfile.mkdtemp(prefix="mr-community-")
    os.environ["DATABASE_PATH"] = str(Path(tmp) / "quotes.db")
    os.environ["ADMIN_TOKEN"] = TOKEN
    get_settings.cache_clear()
    # Sans `with` : pas d'événement startup (pas de seed massif) → seed minimal ici.
    init_db()
    with get_db() as conn:
        for quote, artist, title in SEED:
            insert_quote(conn, quote=quote, artist=artist, title=title)
    ratelimit.set_limit(0)  # SEC-04 neutralisé : les scénarios ci-dessous font > 120 écritures / min
    ratelimit.reset()
    try:
        yield TestClient(app)
    finally:
        ratelimit.set_limit(None)
        ratelimit.reset()
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        get_settings.cache_clear()


@pytest.fixture(scope="module")
def category_id(client):
    cats = client.get(f"{API}/categories").json()
    return cats[0]["id"]


def _pid() -> str:
    return "p-" + uuid.uuid4().hex[:20]


def _submission(category_id: int, **over) -> dict:
    body = {
        "quote": "On lâche rien, même quand la nuit tombe",
        "artist": "Ninho",
        "title": "Lettre à une femme",
        "category_id": category_id,
        "year": 2019,
        "listen_url": "https://open.spotify.com/track/abc123",
        "player_id": _pid(),
        "pseudo": "LexTest",
    }
    body.update(over)
    return body


def _post_submission(client, category_id: int, **over):
    return client.post(f"{API}/submissions", json=_submission(category_id, **over))


def _play_quote(client, pid: str) -> int:
    """Le joueur répond (faux) à la 1re citation du set du jour ; renvoie son id."""
    pack = client.get(f"{API}/daily", params={"date": DAY, "category": CAT}).json()
    qid = pack["quotes"][0]["id"]
    r = client.post(
        f"{API}/daily/answer",
        json={"quote_id": qid, "artist": "zzz", "title": "zzz", "date": DAY, "category_key": CAT, "player_id": pid},
    )
    assert r.status_code == 200, r.text
    return qid


# --- MR-16 : soumission -----------------------------------------------------


def test_submission_valide_en_pending(client, category_id):
    r = _post_submission(client, category_id)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "pending"
    assert data["message"].startswith("Merci")
    listed = client.get(f"{API}/submissions", params={"status": "pending"}, headers=ADMIN).json()
    item = next(s for s in listed["items"] if s["id"] == data["id"])
    assert item["pseudo"] == "LexTest"
    assert item["year"] == "2019"
    assert item["category_id"] == category_id
    assert listed["counts"]["pending"] >= 1


def test_liste_admin_requiert_token(client):
    assert client.get(f"{API}/submissions").status_code == 401


def test_doublon_409_contre_catalogue_et_propositions(client, category_id):
    # Même artiste + même texte normalisés qu'une citation du catalogue (casse/accents/ponctuation)
    r = _post_submission(
        client,
        category_id,
        quote="LE TEMPS, c'est de l'argent et j'ai pas de monnaie !",
        artist="damso",
        title="Autre titre",
    )
    assert r.status_code == 409, r.text
    assert r.json()["detail"] == "Cette punchline existe déjà"
    # Même chose contre une proposition en attente
    first = _post_submission(client, category_id, quote="Une toute nouvelle punchline inédite", artist="Vald")
    assert first.status_code == 201, first.text
    dup = _post_submission(client, category_id, quote="une toute nouvelle punchline inedite", artist="VALD")
    assert dup.status_code == 409
    # Une proposition rejetée ne bloque plus le doublon
    client.post(f"{API}/submissions/{first.json()['id']}/reject", json={"reason": "flou"}, headers=ADMIN)
    again = _post_submission(client, category_id, quote="Une toute nouvelle punchline inédite", artist="Vald")
    assert again.status_code == 201, again.text


def test_url_ecoute_refusee_422(client, category_id):
    for bad in ("http://evil.example.com/x", "ftp://open.spotify.com/track/1", "javascript:alert(1)", "spotify.com/x"):
        r = _post_submission(client, category_id, quote=f"Punchline avec lien douteux {bad}", listen_url=bad)
        assert r.status_code == 422, (bad, r.text)
        assert "Lien d'écoute" in r.json()["detail"]
    for good in (
        "https://open.spotify.com/track/1",
        "https://www.youtube.com/watch?v=1",
        "https://youtu.be/1",
        "https://www.deezer.com/track/1",
        "https://music.apple.com/ca/album/1",
    ):
        assert listen_url_allowed(good), good
    assert listen_url_allowed("")  # optionnel


def test_pseudo_interdit_422(client, category_id):
    r = _post_submission(client, category_id, quote="Punchline signée par un pseudo interdit", pseudo="connard")
    assert r.status_code == 422, r.text
    assert r.json()["detail"] == "Ce pseudo n'est pas autorisé"
    r = _post_submission(client, category_id, quote="Punchline sans pseudo du tout", pseudo="")
    assert r.status_code == 422


def test_validation_champs_422(client, category_id):
    assert _post_submission(client, category_id, quote="Court").status_code == 422
    assert _post_submission(client, category_id, quote="x" * 301).status_code == 422
    assert _post_submission(client, category_id, quote="Punchline datée trop tôt", year=1899).status_code == 422
    assert _post_submission(client, category_id, quote="Punchline du futur", year=date.today().year + 1).status_code == 422
    body = {**_submission(category_id), "quote": "Punchline sans catégorie", "category_id": 999999}
    assert client.post(f"{API}/submissions", json=body).status_code == 422


def test_limite_10_par_joueur_par_jour_429(client, category_id):
    pid = _pid()
    for i in range(SUBMISSIONS_PER_DAY):
        r = _post_submission(client, category_id, quote=f"Punchline numéro {i} d'un joueur prolifique", player_id=pid)
        assert r.status_code == 201, (i, r.text)
    r = _post_submission(client, category_id, quote="Punchline de trop pour aujourd'hui", player_id=pid)
    assert r.status_code == 429, r.text
    assert "10 propositions" in r.json()["detail"]
    # Un autre joueur n'est pas bloqué
    r = _post_submission(client, category_id, quote="Punchline d'un autre joueur tranquille")
    assert r.status_code == 201


# --- MR-16 : relecture admin ------------------------------------------------


def test_approve_cree_citation_points_badge(client, category_id):
    pid = _pid()
    r = _post_submission(
        client,
        category_id,
        quote="Punchline approuvée par l'admin ce soir",
        artist="SCH",
        title="A7",
        year=2015,
        listen_url="https://youtu.be/approved",
        player_id=pid,
        pseudo="Contrib",
    )
    assert r.status_code == 201, r.text
    sid = r.json()["id"]
    assert client.post(f"{API}/submissions/{sid}/approve").status_code == 401

    before = client.get(f"{API}/players/{pid}/rewards").json()
    assert before == {"player_id": pid, "points": 0, "badges": []}

    r = client.post(f"{API}/submissions/{sid}/approve", json={"rarity": "rare"}, headers=ADMIN)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["submission"]["status"] == "approved"
    q = data["quote"]
    assert data["submission"]["quote_id"] == q["id"]
    assert q["artist"] == "SCH" and q["title"] == "A7"
    assert q["listen_url"] == "https://youtu.be/approved"
    assert q["rarity"] == "rare"
    assert q["contributor_pseudo"] == "Contrib"
    assert q["hints"]["year"] == "2015"
    assert category_id in q["category_ids"]
    assert data["rewards"]["points"] == 50
    assert data["rewards"]["badges"] == ["contributeur"]

    # Citation jouable : présente dans le catalogue, avec submission_id en base
    with get_db() as conn:
        row = conn.execute("SELECT contributor_pseudo, submission_id FROM quotes WHERE id = ?", (q["id"],)).fetchone()
    assert row["contributor_pseudo"] == "Contrib" and row["submission_id"] == sid
    # Le public ne voit pas artiste/titre (SEC-01 conservé)
    pub = client.get(f"{API}/quotes/{q['id']}").json()
    assert "artist" not in pub and "title" not in pub

    after = client.get(f"{API}/players/{pid}/rewards").json()
    assert after["points"] == 50 and after["badges"] == ["contributeur"]
    # Une seconde approbation du même id → 409 ; 2e contribution → +50, badge unique
    assert client.post(f"{API}/submissions/{sid}/approve", headers=ADMIN).status_code == 409
    r2 = _post_submission(client, category_id, quote="Deuxième punchline du même contributeur", player_id=pid, pseudo="Contrib")
    client.post(f"{API}/submissions/{r2.json()['id']}/approve", headers=ADMIN)
    again = client.get(f"{API}/players/{pid}/rewards").json()
    assert again["points"] == 100 and again["badges"] == ["contributeur"]


def test_reject(client, category_id):
    r = _post_submission(client, category_id, quote="Punchline destinée à être rejetée")
    sid = r.json()["id"]
    assert client.post(f"{API}/submissions/{sid}/reject", json={"reason": "hors sujet"}).status_code == 401
    r = client.post(f"{API}/submissions/{sid}/reject", json={"reason": "hors sujet"}, headers=ADMIN)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected" and r.json()["reason"] == "hors sujet"
    assert client.post(f"{API}/submissions/{sid}/approve", headers=ADMIN).status_code == 409
    assert client.post(f"{API}/submissions/999999/reject", headers=ADMIN).status_code == 404
    rejected = client.get(f"{API}/submissions", params={"status": "rejected"}, headers=ADMIN).json()
    assert any(s["id"] == sid for s in rejected["items"])


# --- MR-17 : vote -----------------------------------------------------------


def test_vote_sans_avoir_joue_403(client):
    pack = client.get(f"{API}/daily", params={"date": DAY, "category": CAT}).json()
    qid = pack["quotes"][0]["id"]
    r = client.post(f"{API}/quotes/{qid}/vote", json={"player_id": _pid(), "value": 1})
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "Réponds d'abord à cette citation"
    assert client.post(f"{API}/quotes/999999/vote", json={"player_id": _pid(), "value": 1}).status_code == 404


def test_vote_une_fois_puis_revote(client):
    pid = _pid()
    qid = _play_quote(client, pid)
    assert client.post(f"{API}/quotes/{qid}/vote", json={"player_id": pid, "value": 2}).status_code == 422
    r = client.post(f"{API}/quotes/{qid}/vote", json={"player_id": pid, "value": 1})
    assert r.status_code == 200, r.text
    assert r.json()["my_vote"] == 1
    up0, down0 = r.json()["up"], r.json()["down"]
    # Même vote répété : aucun doublon
    r = client.post(f"{API}/quotes/{qid}/vote", json={"player_id": pid, "value": 1})
    assert (r.json()["up"], r.json()["down"]) == (up0, down0)
    # Revote 👎 : bascule, toujours un seul vote pour ce joueur
    r = client.post(f"{API}/quotes/{qid}/vote", json={"player_id": pid, "value": -1})
    assert r.json()["my_vote"] == -1
    assert (r.json()["up"], r.json()["down"]) == (up0 - 1, down0 + 1)
    with get_db() as conn:
        n = conn.execute("SELECT COUNT(*) FROM quote_votes WHERE quote_id = ? AND player_id = ?", (qid, pid)).fetchone()[0]
    assert n == 1


def test_reveals_contiennent_contributor_et_my_vote(client):
    """Le payload `reveals` de GET /daily/reveal expose `contributor_pseudo` et `my_vote`."""
    pid = _pid()
    pack = client.get(f"{API}/daily", params={"date": DAY, "category": CAT}).json()
    answers = []
    for q in pack["quotes"]:
        r = client.post(
            f"{API}/daily/answer",
            json={"quote_id": q["id"], "artist": "zzz", "title": "zzz", "date": DAY, "category_key": CAT, "player_id": pid},
        )
        answers.append(r.json())
    qid = pack["quotes"][0]["id"]
    client.post(f"{API}/quotes/{qid}/vote", json={"player_id": pid, "value": 1})
    res = client.post(
        f"{API}/daily/result",
        json={"player_id": pid, "pseudo": "", "score": 0, "correct": 0, "hints": 0, "time_ms": 60_000, "grid": "", "date": DAY, "category_key": CAT},
    )
    assert res.status_code == 200, res.text
    reveals = res.json()["reveals"]
    assert len(reveals) == 5
    assert all("contributor_pseudo" in r and "my_vote" in r for r in reveals)
    mine = next(r for r in reveals if r["id"] == qid)
    assert mine["my_vote"] == 1
    assert all(r["my_vote"] is None for r in reveals if r["id"] != qid)
    r = client.get(f"{API}/daily/reveal", params={"date": DAY, "category_key": CAT, "player_id": pid})
    assert r.status_code == 200
    assert next(x for x in r.json()["reveals"] if x["id"] == qid)["my_vote"] == 1


def test_flagged_seuil_30_votes_et_40_pourcent(client):
    assert client.get(f"{API}/quotes/flagged").status_code == 401
    pack = client.get(f"{API}/daily", params={"date": DAY, "category": CAT}).json()
    qid = pack["quotes"][1]["id"]

    def vote(value: int):
        pid = _pid()
        r = client.post(
            f"{API}/daily/answer",
            json={"quote_id": qid, "artist": "zzz", "title": "zzz", "date": DAY, "category_key": CAT, "player_id": pid},
        )
        assert r.status_code == 200, r.text
        r = client.post(f"{API}/quotes/{qid}/vote", json={"player_id": pid, "value": value})
        assert r.status_code == 200, r.text
        return r.json()

    # 29 votes dont 12 👎 (41 %) : sous le seuil de 30 → pas signalée
    for i in range(29):
        last = vote(-1 if i < 12 else 1)
    assert last["total"] == 29
    ids = [q["id"] for q in client.get(f"{API}/quotes/flagged", headers=ADMIN).json()]
    assert qid not in ids
    # 30e vote 🔥 → 12/30 = 40 % exactement : pas strictement > 40 % → pas signalée
    last = vote(1)
    assert last["total"] == 30
    ids = [q["id"] for q in client.get(f"{API}/quotes/flagged", headers=ADMIN).json()]
    assert qid not in ids
    # 31e vote 👎 → 13/31 ≈ 41,9 % → signalée
    vote(-1)
    flagged = client.get(f"{API}/quotes/flagged", headers=ADMIN).json()
    item = next(q for q in flagged if q["id"] == qid)
    assert item["total"] == 31 and item["down"] == 13
    assert item["down_ratio"] > 0.40
    assert item["artist"] and item["title"]  # vue admin complète
