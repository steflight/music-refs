"""Lot H — Security by design (SEC-01 → SEC-04).

Lancement : cd backend && python3 -m pytest tests -q
(ou python3 -m unittest discover -s tests). Base SQLite temporaire via DATABASE_PATH.
"""

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

import config
import ratelimit
from main import app

# L'environnement (base temporaire, token) est posé dans setUpClass et RESTAURÉ dans
# tearDownClass : rien n'est modifié à l'import, pour ne pas perturber les autres modules.
TOKEN = "sec-test-token"
ADMIN = {"X-Admin-Token": TOKEN}
FORBIDDEN_KEYS = {"artist", "title", "listen_url"}
_ENV_KEYS = ("DATABASE_PATH", "ADMIN_TOKEN", "RATE_LIMIT_PER_MINUTE")


class SecurityBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved_env = {k: os.environ.get(k) for k in _ENV_KEYS}
        cls._tmp = tempfile.mkdtemp(prefix="mr-sec-")
        os.environ["DATABASE_PATH"] = os.path.join(cls._tmp, "quotes.db")
        os.environ["ADMIN_TOKEN"] = TOKEN
        os.environ["RATE_LIMIT_PER_MINUTE"] = "120"
        config.get_settings.cache_clear()
        ratelimit.set_limit(None)
        ratelimit.reset()
        cls.client = TestClient(app)
        cls.client.__enter__()  # startup → init_db + seed
        quotes = cls.client.get("/api/music-refs/quotes", headers=ADMIN).json()
        assert quotes, "le seed doit fournir des punchlines"
        cls.full = quotes[0]  # avec artiste/titre (admin)
        cls.qid = cls.full["id"]

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        ratelimit.set_limit(None)
        ratelimit.reset()
        for k, v in cls._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        config.get_settings.cache_clear()

    def setUp(self):
        ratelimit.set_limit(None)
        ratelimit.reset()


class TestSec01Catalogue(SecurityBase):
    def test_catalogue_public_sans_reponses(self):
        res = self.client.get("/api/music-refs/quotes")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data)
        for q in data:
            self.assertFalse(FORBIDDEN_KEYS & set(q.keys()), q.keys())
            self.assertIn("quote", q)
            self.assertIn("hints", q)
        # Contrat strict : aucun autre champ que ceux-ci (pas de réponse « sous un autre nom »).
        # La punchline elle-même et les indices payants (album d'un single = titre) sont des
        # données de jeu, pas une fuite de l'API.
        import json

        admin_rows = {q["id"]: q for q in self.client.get("/api/music-refs/quotes", headers=ADMIN).json()}
        for q in data:
            self.assertEqual(set(q.keys()), {"id", "quote", "hints", "rarity", "category_ids"})
            self.assertEqual(set(q["hints"].keys()), {"year", "genre", "album", "initials"})
            ref = admin_rows[q["id"]]
            others = json.dumps({k: v for k, v in q.items() if k not in ("hints", "quote")}, ensure_ascii=False).lower()
            self.assertNotIn(ref["artist"].lower(), others)
            self.assertNotIn(ref["title"].lower(), others)

    def test_random_et_detail_publics_sans_reponses(self):
        for path in ("/api/music-refs/random", f"/api/music-refs/quotes/{self.qid}"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, path)
            self.assertFalse(FORBIDDEN_KEYS & set(res.json().keys()), path)

    def test_catalogue_admin_avec_reponses(self):
        res = self.client.get("/api/music-refs/quotes", headers=ADMIN)
        self.assertEqual(res.status_code, 200)
        q = res.json()[0]
        self.assertIn("artist", q)
        self.assertIn("title", q)
        self.assertIn("listen_url", q)

    def test_mauvais_token_traite_comme_public(self):
        res = self.client.get("/api/music-refs/quotes", headers={"X-Admin-Token": "faux"})
        self.assertEqual(res.status_code, 200)
        self.assertFalse(FORBIDDEN_KEYS & set(res.json()[0].keys()))

    def test_options_quiz_sans_fuite(self):
        res = self.client.get(f"/api/music-refs/quotes/{self.qid}/options?count=4")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(set(data.keys()), {"artists", "titles"})
        self.assertEqual(len(data["artists"]), 4)
        self.assertEqual(len(data["titles"]), 4)
        self.assertEqual(len(set(data["artists"])), 4)
        self.assertIn(self.full["artist"], data["artists"])
        self.assertIn(self.full["title"], data["titles"])
        # Sur plusieurs tirages, la bonne réponse n'est pas toujours en tête (mélange)
        positions = set()
        for _ in range(25):
            d = self.client.get(f"/api/music-refs/quotes/{self.qid}/options").json()
            positions.add(d["artists"].index(self.full["artist"]))
        self.assertGreater(len(positions), 1)

    def test_options_404(self):
        self.assertEqual(self.client.get("/api/music-refs/quotes/999999/options").status_code, 404)


class TestSec02VerdictSolo(SecurityBase):
    def setUp(self):
        super().setUp()
        self.client.patch(f"/api/music-refs/quotes/{self.qid}", json={"rarity": "commune"}, headers=ADMIN)

    def _answer(self, **body):
        return self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json=body)

    def test_verdict_juste(self):
        res = self._answer(artist=self.full["artist"], title=self.full["title"])
        self.assertEqual(res.status_code, 200)
        v = res.json()
        self.assertTrue(v["artist_ok"] and v["title_ok"] and v["fully_correct"])
        self.assertEqual(v["points"], 250)
        self.assertFalse(v["half_points"])
        self.assertEqual(v["reveal"]["artist"], self.full["artist"])

    def test_verdict_faux(self):
        v = self._answer(artist="Zzzz Qqqq", title="Wwww Kkkk").json()
        self.assertFalse(v["artist_ok"] or v["title_ok"] or v["fully_correct"])
        self.assertEqual(v["points"], 0)
        self.assertIsNone(v["reveal"])
        self.assertNotIn(self.full["artist"], v["message"])

    def test_artiste_juste_titre_faux_demi_points(self):
        v = self._answer(artist=self.full["artist"], title="Titre complètement faux").json()
        self.assertTrue(v["artist_ok"])
        self.assertFalse(v["title_ok"])
        self.assertTrue(v["half_points"])
        self.assertEqual(v["points"], 100)  # moitié de 200 (MR-11)
        self.assertIn("moitié", v["message"])
        self.assertIsNone(v["reveal"])

    def test_tolerance_mr11(self):
        # casse + accents + article initial + faute de frappe (Levenshtein ≤ 2 si ≥ 6 lettres)
        artist = self.full["artist"]
        variants = [artist.upper(), artist.lower(), "le " + artist]
        if len(artist) >= 6:
            variants.append(artist[:-1] + "x")
        for var in variants:
            v = self._answer(artist=var, title="").json()
            self.assertTrue(v["artist_ok"], var)

    def test_penalite_indices(self):
        v = self._answer(artist=self.full["artist"], title=self.full["title"], hints_used=2).json()
        self.assertEqual(v["points"], 210)  # 250 − 2×20

    def test_reponse_vide_400_et_404(self):
        self.assertEqual(self._answer(artist="", title="").status_code, 400)
        self.assertEqual(
            self.client.post("/api/music-refs/quotes/999999/answer", json={"artist": "x"}).status_code, 404
        )

    def test_reveal_abandon(self):
        res = self.client.post(f"/api/music-refs/quotes/{self.qid}/reveal")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["artist"], self.full["artist"])


class TestSec03Salon(SecurityBase):
    def _party(self, rounds=3):
        cats = self.client.get("/api/music-refs/categories").json()
        cat = next(c for c in cats if c["quote_count"] >= 3)
        host = self.client.post(
            "/api/music-refs/parties",
            json={"category_id": cat["id"], "host_name": "Hôte", "round_limit": rounds},
        ).json()
        code = host["code"]
        guest = self.client.post("/api/music-refs/parties/join", json={"code": code, "player_name": "Invité"}).json()
        self.client.post(f"/api/music-refs/parties/{code}/start", json={"host_token": host["me"]["host_token"]})
        quotes = self.client.get(f"/api/music-refs/parties/{code}/quotes").json()
        return code, host["me"]["player_token"], guest["me"]["player_token"], quotes

    def _full(self, qid):
        # Rareté forcée à « commune » (×1) pour un barème prévisible
        self.client.patch(f"/api/music-refs/quotes/{qid}", json={"rarity": "commune"}, headers=ADMIN)
        return self.client.get(f"/api/music-refs/quotes/{qid}", headers=ADMIN).json()

    def test_quotes_du_salon_sans_reponses(self):
        _, _, _, quotes = self._party()
        self.assertTrue(quotes)
        for q in quotes:
            self.assertFalse(FORBIDDEN_KEYS & set(q.keys()))

    def test_score_calcule_par_le_serveur(self):
        code, host_tok, guest_tok, quotes = self._party()
        q0 = self._full(quotes[0]["id"])
        # Réponse fausse → 0
        r = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": host_tok, "quote_id": q0["id"], "artist": "Zzzz", "title": "Qqqq"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["score"], 0)
        self.assertFalse(r.json()["artist_ok"])
        # Artiste seul → 100, puis complément → total 250
        r = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": host_tok, "quote_id": q0["id"], "artist": q0["artist"], "title": ""},
        ).json()
        self.assertTrue(r["half_points"])
        self.assertEqual(r["awarded"], 100)
        self.assertEqual(r["score"], 100)
        r = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": host_tok, "quote_id": q0["id"], "artist": q0["artist"], "title": q0["title"]},
        ).json()
        self.assertTrue(r["fully_correct"])
        self.assertEqual(r["awarded"], 150)
        self.assertEqual(r["score"], 250)
        self.assertEqual(r["streak"], 1)
        self.assertEqual(r["reveal"]["title"], q0["title"])
        # Rejouer la même punchline résolue → 409, pas de double comptage
        r = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": host_tok, "quote_id": q0["id"], "artist": q0["artist"], "title": q0["title"]},
        )
        self.assertEqual(r.status_code, 409)
        # Série : 2e punchline complète → 250 + bonus (2−1)×50
        q1 = self._full(quotes[1]["id"])
        r = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": host_tok, "quote_id": q1["id"], "artist": q1["artist"], "title": q1["title"]},
        ).json()
        self.assertEqual(r["streak"], 2)
        self.assertEqual(r["awarded"], 300)
        self.assertEqual(r["score"], 550)
        # Classement en direct : le snapshot du salon reflète le score serveur
        snap = self.client.get(f"/api/music-refs/parties/{code}").json()
        scores = {p["name"]: p["score"] for p in snap["players"]}
        self.assertEqual(scores["Hôte"], 550)
        self.assertEqual(scores["Invité"], 0)

    def test_score_client_ignore(self):
        code, host_tok, _, _ = self._party()
        r = self.client.post(
            f"/api/music-refs/parties/{code}/score",
            json={"player_token": host_tok, "score": 99999, "progress": 2},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["me"]["score"], 0)
        self.assertEqual(r.json()["me"]["progress"], 2)

    def test_skip_revele_et_gele(self):
        code, host_tok, _, quotes = self._party()
        q0 = self._full(quotes[0]["id"])
        r = self.client.post(
            f"/api/music-refs/parties/{code}/skip",
            json={"player_token": host_tok, "quote_id": q0["id"]},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["reveal"]["artist"], q0["artist"])
        # Répondre après révélation ne rapporte rien
        r = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": host_tok, "quote_id": q0["id"], "artist": q0["artist"], "title": q0["title"]},
        ).json()
        self.assertEqual(r["awarded"], 0)
        self.assertEqual(r["score"], 0)

    def test_garde_fous(self):
        code, host_tok, _, quotes = self._party()
        bad_tok = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": "x" * 20, "quote_id": quotes[0]["id"], "artist": "a"},
        )
        self.assertEqual(bad_tok.status_code, 404)
        other_ids = {q["id"] for q in quotes}
        foreign = next(q["id"] for q in self.client.get("/api/music-refs/quotes").json() if q["id"] not in other_ids)
        r = self.client.post(
            f"/api/music-refs/parties/{code}/answer",
            json={"player_token": host_tok, "quote_id": foreign, "artist": "a"},
        )
        self.assertEqual(r.status_code, 400)


class TestSec04RateLimit(SecurityBase):
    def test_429_apres_depassement(self):
        ratelimit.set_limit(5)
        ratelimit.reset()
        body = {"artist": "x", "title": ""}
        codes = [
            self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json=body).status_code
            for _ in range(6)
        ]
        self.assertEqual(codes[:5], [200] * 5)
        self.assertEqual(codes[5], 429)
        res = self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json=body)
        self.assertEqual(res.status_code, 429)
        self.assertIn("Trop de requêtes", res.json()["detail"])
        self.assertIn("Retry-After", res.headers)

    def test_get_health_et_admin_exemptes(self):
        ratelimit.set_limit(1)
        ratelimit.reset()
        self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json={"artist": "x"})
        self.assertEqual(
            self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json={"artist": "x"}).status_code, 429
        )
        self.assertEqual(self.client.get("/api/music-refs/quotes").status_code, 200)
        self.assertEqual(self.client.get("/health").status_code, 200)
        # Route admin authentifiée : exemptée
        r = self.client.patch(f"/api/music-refs/quotes/{self.qid}", json={"rarity": "commune"}, headers=ADMIN)
        self.assertEqual(r.status_code, 200)

    def test_ip_par_x_forwarded_for(self):
        ratelimit.set_limit(1)
        ratelimit.reset()
        h1 = {"X-Forwarded-For": "203.0.113.1, 10.0.0.2"}
        h2 = {"X-Forwarded-For": "203.0.113.2"}
        self.assertEqual(self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json={"artist": "x"}, headers=h1).status_code, 200)
        self.assertEqual(self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json={"artist": "x"}, headers=h1).status_code, 429)
        self.assertEqual(self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json={"artist": "x"}, headers=h2).status_code, 200)

    def test_limite_zero_desactive(self):
        ratelimit.set_limit(0)
        ratelimit.reset()
        for _ in range(10):
            self.assertEqual(self.client.post(f"/api/music-refs/quotes/{self.qid}/answer", json={"artist": "x"}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
