"""MR-19 — tests d'ingestion des événements et des statistiques de la boucle."""

import os
import tempfile
from datetime import timedelta
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="mr-events-")
os.environ["DATABASE_PATH"] = str(Path(_TMP) / "test.db")
os.environ["ADMIN_TOKEN"] = "test-admin-token"

from config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from daily import today_toronto  # noqa: E402
from db import EVENT_NAMES, compute_stats, get_db, init_db, purge_old_events  # noqa: E402
from main import app  # noqa: E402

ADMIN = {"X-Admin-Token": "test-admin-token"}
PLAYER = "11111111-2222-4333-8444-555555555555"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_events():
    with get_db() as conn:
        conn.execute("DELETE FROM events")
    yield


def _batch(events, player_id=PLAYER, tz="America/Toronto"):
    return {"player_id": player_id, "tz": tz, "events": events}


def _insert(conn, player_id, name, day, props="{}"):
    conn.execute(
        "INSERT INTO events (ts, day, name, player_id, props_json) VALUES (?, ?, ?, ?, ?)",
        (f"{day}T12:00:00-04:00", day, name, player_id, props),
    )


# --- Ingestion -------------------------------------------------------------


def test_post_events_valid_batch_is_stored_with_server_timestamp(client):
    r = client.post(
        "/api/music-refs/events",
        json=_batch(
            [
                {"name": "daily_started", "props": {"edition": 12}},
                {"name": "daily_completed", "props": {"score": 40, "hints": 1, "timeMs": 61000}},
            ]
        ),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] == 2 and body["rejected"] == 0
    with get_db() as conn:
        rows = conn.execute("SELECT ts, day, name, player_id, props_json FROM events ORDER BY id").fetchall()
    assert [row["name"] for row in rows] == ["daily_started", "daily_completed"]
    assert all(row["player_id"] == PLAYER for row in rows)
    assert all(row["day"] == body["day"] for row in rows)
    assert all(row["ts"].startswith(body["day"]) for row in rows)  # horodatage serveur
    assert '"score":40' in rows[1]["props_json"]
    assert '"_tz":"America/Toronto"' in rows[1]["props_json"]


def test_post_events_unknown_name_is_rejected_individually(client):
    r = client.post(
        "/api/music-refs/events",
        json=_batch([{"name": "pageview"}, {"name": "share_clicked", "props": {"channel": "whatsapp"}}]),
    )
    assert r.status_code == 200
    assert r.json() == {"accepted": 1, "rejected": 1, "day": r.json()["day"]}
    with get_db() as conn:
        names = [row["name"] for row in conn.execute("SELECT name FROM events").fetchall()]
    assert names == ["share_clicked"]


def test_post_events_whitelist_matches_spec():
    assert EVENT_NAMES == {
        "daily_started", "daily_completed", "share_clicked", "share_landed", "streak_milestone",
        "challenge_created", "challenge_accepted", "notif_optin", "quote_submitted",
    }


def test_post_events_props_over_1kb_rejected_and_nested_dropped(client):
    big = {"channel": "x" * 300, "a": "y" * 300, "b": "z" * 300, "c": "w" * 300}
    r = client.post(
        "/api/music-refs/events",
        json=_batch(
            [
                {"name": "share_clicked", "props": big},
                {"name": "share_landed", "props": {"ref": "share", "nested": {"pii": "no"}, "list": [1, 2]}},
            ]
        ),
    )
    assert r.status_code == 200
    assert r.json()["accepted"] == 1 and r.json()["rejected"] == 1
    with get_db() as conn:
        row = conn.execute("SELECT props_json FROM events").fetchone()
    assert "nested" not in row["props_json"] and "list" not in row["props_json"]
    assert '"ref":"share"' in row["props_json"]


def test_post_events_batch_over_50_or_empty_is_422(client):
    too_many = [{"name": "daily_started"} for _ in range(51)]
    assert client.post("/api/music-refs/events", json=_batch(too_many)).status_code == 422
    assert client.post("/api/music-refs/events", json=_batch([])).status_code == 422


def test_post_events_invalid_player_id_or_tz(client):
    r = client.post("/api/music-refs/events", json=_batch([{"name": "daily_started"}], player_id="short"))
    assert r.status_code == 422
    r = client.post("/api/music-refs/events", json=_batch([{"name": "daily_started"}], player_id="a" * 12 + " ;drop"))
    assert r.status_code == 422
    r = client.post("/api/music-refs/events", json=_batch([{"name": "daily_started"}], tz="Mars/Olympus"))
    assert r.status_code == 200
    with get_db() as conn:
        row = conn.execute("SELECT props_json FROM events").fetchone()
    assert '"_tz":"UTC"' in row["props_json"]


# --- Purge -----------------------------------------------------------------


def test_purge_removes_events_older_than_180_days():
    today = today_toronto()  # jour du jeu (America/Toronto), pas celui de l'hôte
    with get_db() as conn:
        _insert(conn, PLAYER, "daily_started", (today - timedelta(days=181)).isoformat())
        _insert(conn, PLAYER, "daily_started", (today - timedelta(days=179)).isoformat())
        _insert(conn, PLAYER, "daily_started", today.isoformat())
    init_db()  # la purge tourne au démarrage
    with get_db() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2
        assert purge_old_events(conn, days=0) == 1  # supprime D-179 ; aujourd'hui exclu (day < aujourd'hui)
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


# --- Stats -----------------------------------------------------------------


def test_stats_requires_admin_token(client):
    assert client.get("/api/music-refs/stats").status_code == 401
    assert client.get("/api/music-refs/stats", headers={"X-Admin-Token": "nope"}).status_code == 401
    r = client.get("/api/music-refs/stats?days=7", headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["days"] == 7 and len(body["dau"]["series"]) == 7 and len(body["by_day"]) == 7
    assert set(body["totals"]) == EVENT_NAMES
    assert client.get("/api/music-refs/stats?days=0", headers=ADMIN).status_code == 422


def test_stats_on_synthetic_dataset_with_known_retention(client):
    """Jeu de données : aujourd'hui = D0. Fenêtre 30 jours.

    Cohorte D-40 : p_old (hors fenêtre, ignoré).
    Cohorte D-31 : p_a — premier daily_completed à D-31, revenu D-30, D-24, D-1 → J1 oui, J7 oui, J30 oui.
                   p_b — premier à D-31, revenu D-29 seulement → J1 non (mais « ou plus tard » oui), J7 non/oui, J30 non/non.
    Cohorte D-10 : p_c — revenu D-9 → J1 oui ; J7 (D-3) non ; J30 pas mûr.
                   p_d — jamais revenu → J1 non, J7 non.
    Cohorte D0  : p_e — pas mûr pour J1.
    """
    today = today_toronto()  # jour du jeu (America/Toronto), pas celui de l'hôte
    d = lambda n: (today - timedelta(days=n)).isoformat()  # noqa: E731
    with get_db() as conn:
        _insert(conn, "p_old_000001", "daily_completed", d(40))
        for day in (31, 30, 24, 1):
            _insert(conn, "p_a_00000001", "daily_completed", d(day))
        for day in (31, 29):
            _insert(conn, "p_b_00000001", "daily_completed", d(day))
        for day in (10, 9):
            _insert(conn, "p_c_00000001", "daily_completed", d(day))
        _insert(conn, "p_d_00000001", "daily_completed", d(10))
        _insert(conn, "p_e_00000001", "daily_completed", d(0))
        _insert(conn, "p_e_00000001", "daily_completed", d(0))  # 2e catégorie le même jour → 1 seul DAU
        # activité sans fin de partie
        _insert(conn, "p_f_00000001", "daily_started", d(0))
        _insert(conn, "p_f_00000001", "daily_started", d(7))
        _insert(conn, "p_g_00000001", "daily_started", d(7))
        # partages : p_a partage 2 fois le même jour (1 partie partagée), p_c 1 fois
        _insert(conn, "p_a_00000001", "share_clicked", d(1), '{"channel":"whatsapp"}')
        _insert(conn, "p_a_00000001", "share_clicked", d(1), '{"channel":"copy"}')
        _insert(conn, "p_c_00000001", "share_clicked", d(9), '{"channel":"share"}')
        for _ in range(3):
            _insert(conn, "p_z_00000001", "share_landed", d(2), '{"ref":"share"}')
        _insert(conn, "p_a_00000001", "quote_submitted", d(2))
        _insert(conn, "p_a_00000001", "notif_optin", d(2))
        stats = compute_stats(conn, 30, today=today)

    # Fenêtre = D-29 .. D0 (30 jours)
    assert stats["from"] == d(29) and stats["to"] == d(0)
    # DAU
    assert stats["dau"]["today"] == 2  # p_e + p_f
    assert stats["dau"]["j7"] == 2  # p_f + p_g
    series = {p["day"]: p["dau"] for p in stats["dau"]["series"]}
    assert series[d(29)] == 1 and series[d(10)] == 2 and series[d(9)] == 1 and series[d(15)] == 0
    # Rétention : cohortes dans la fenêtre = p_c, p_d (D-10), p_e (D0). p_a/p_b (D-31) hors fenêtre.
    ret = stats["retention"]
    assert ret["j1"] == {"cohort": 2, "returned": 1, "pct": 50.0, "pct_or_later": 50.0}
    assert ret["j7"] == {"cohort": 2, "returned": 0, "pct": 0.0, "pct_or_later": 0.0}
    assert ret["j30"] == {"cohort": 0, "returned": 0, "pct": 0.0, "pct_or_later": 0.0}
    # Partage : parties (joueur, jour) terminées dans la fenêtre = p_a D-24, p_a D-1, p_b D-29, p_c D-10,
    # p_c D-9, p_d D-10, p_e D0 = 7 ; partagées = p_a D-1, p_c D-9 = 2 → 28.6 %
    assert stats["share"]["games"] == 8 and stats["share"]["games_distinct"] == 7
    assert stats["share"]["shared_distinct"] == 2 and stats["share"]["pct"] == 28.6
    # k-factor = share_landed / daily_completed = 3 / 8
    assert stats["k_factor"] == 0.375
    assert stats["totals"]["share_clicked"] == 3 and stats["totals"]["quote_submitted"] == 1
    assert stats["totals"]["challenge_created"] == 0
    row = next(p for p in stats["by_day"] if p["day"] == d(1))
    assert row == {"day": d(1), "dau": 1, "counts": {"daily_completed": 1, "share_clicked": 2}}


def test_stats_retention_window_includes_31_day_cohorts_when_days_is_60(client):
    today = today_toronto()  # jour du jeu (America/Toronto), pas celui de l'hôte
    d = lambda n: (today - timedelta(days=n)).isoformat()  # noqa: E731
    with get_db() as conn:
        for day in (31, 30, 24, 1):
            _insert(conn, "p_a_00000001", "daily_completed", d(day))
        for day in (31, 29):
            _insert(conn, "p_b_00000001", "daily_completed", d(day))
        stats = compute_stats(conn, 60, today=today)
    ret = stats["retention"]
    assert ret["j1"] == {"cohort": 2, "returned": 1, "pct": 50.0, "pct_or_later": 100.0}
    assert ret["j7"] == {"cohort": 2, "returned": 1, "pct": 50.0, "pct_or_later": 50.0}
    assert ret["j30"] == {"cohort": 2, "returned": 1, "pct": 50.0, "pct_or_later": 50.0}


def test_stats_endpoint_matches_compute(client):
    today = today_toronto()  # jour du jeu (America/Toronto), pas celui de l'hôte
    with get_db() as conn:
        _insert(conn, PLAYER, "daily_started", today.isoformat())
    r = client.get("/api/music-refs/stats?days=3", headers=ADMIN)
    assert r.status_code == 200
    assert r.json()["dau"]["today"] == 1
    assert r.json()["timezone"] == "America/Toronto"


def test_stats_page_is_served(client):
    r = client.get("/stats.html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "X-Admin-Token" in r.text and "/api/music-refs/stats" in r.text
