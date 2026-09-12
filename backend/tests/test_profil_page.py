"""Lot E — MR-15 : la page /profil est servie (route + alias).

Lancer : cd backend && python3 -m pytest tests -q
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

_TMP = tempfile.mkdtemp(prefix="mr-profil-")
os.environ["DATABASE_PATH"] = str(Path(_TMP) / "quotes.db")

from config import get_settings  # noqa: E402

get_settings.cache_clear()

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def test_profil_html_route_serves_page():
    with TestClient(app) as client:
        r = client.get("/profil.html")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Mon profil" in r.text
    assert "profileStore.js" in r.text


def test_profil_alias_serves_same_page():
    with TestClient(app) as client:
        r = client.get("/profil")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "Télécharger l'image" in r.text
