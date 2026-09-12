from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from db import init_db, seed_from_json
from ratelimit import RateLimitMiddleware
from routes.categories import router as categories_router
from routes.daily import router as daily_router
from routes.events import router as events_router
from routes.parties import router as parties_router
from routes.quotes import router as quotes_router

AVAILABLE_ENDPOINTS = [
    "GET /",
    "GET /health",
    "GET /docs",
    "GET /api/music-refs/quotes",
    "GET /api/music-refs/quotes/{id}/options",
    "POST /api/music-refs/quotes/{id}/answer",
    "POST /api/music-refs/quotes/{id}/reveal",
    "GET /api/music-refs/random",
    "GET /api/music-refs/categories",
    "GET /api/music-refs/daily",
    "POST /api/music-refs/daily/answer",
    "POST /api/music-refs/daily/result",
    "GET /api/music-refs/daily/reveal",
    "POST /api/music-refs/daily/challenge",
    "POST /api/music-refs/parties",
    "POST /api/music-refs/parties/join",
    "POST /api/music-refs/parties/{code}/answer",
    "POST /api/music-refs/parties/{code}/skip",
    "POST /api/music-refs/import",
    "POST /api/music-refs/quotes",
    "PATCH /api/music-refs/quotes/{id}",
    "DELETE /api/music-refs/quotes/{id}",
    "POST /api/music-refs/events",
    "GET /api/music-refs/stats?days=30",
]

app = FastAPI(
    title="Music Refs API",
    description="Punchlines, catégories, parties & Refs du jour",
    version="1.4.0",
)

settings = get_settings()
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
# SEC-04 — limitation de débit (ajouté AVANT CORS pour que CORS reste le plus externe)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quotes_router)
app.include_router(categories_router)
app.include_router(parties_router)
app.include_router(daily_router)
app.include_router(events_router)


def frontend_root() -> Path:
    candidates = [
        Path("/frontend"),
        Path(__file__).resolve().parent.parent,
        Path("/workspace/music-refs"),
    ]
    for root in candidates:
        if (root / "index.html").exists():
            return root
    return Path("/frontend")


FRONT = frontend_root()


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed_path = Path(__file__).resolve().parent / "seed_quotes.json"
    seed_from_json(seed_path)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "Music Refs API", "version": "1.4.0"}


@app.get("/")
async def root(request: Request):
    accept = (request.headers.get("accept") or "").lower()
    wants_json = "application/json" in accept and "text/html" not in accept
    if wants_json:
        return JSONResponse({"status": "ok", "service": "Music Refs API", "version": "1.4.0"})
    index = FRONT / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return JSONResponse({"status": "ok", "service": "Music Refs API"})


@app.get("/admin.html")
async def admin_page():
    page = FRONT / "admin.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse(
        {"error": "Not Found", "status_code": 404, "available_endpoints": AVAILABLE_ENDPOINTS},
        status_code=404,
    )


@app.get("/daily.html")
async def daily_page():
    page = FRONT / "daily.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse(
        {"error": "Not Found", "status_code": 404, "available_endpoints": AVAILABLE_ENDPOINTS},
        status_code=404,
    )


@app.get("/party.html")
async def party_page():
    page = FRONT / "party.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse(
        {"error": "Not Found", "status_code": 404, "available_endpoints": AVAILABLE_ENDPOINTS},
        status_code=404,
    )


@app.get("/stats.html")
async def stats_page():
    """MR-19 — tableau de bord de la boucle (token admin requis pour les données)."""
    page = FRONT / "stats.html"
    if page.exists():
        return FileResponse(page)
    return JSONResponse(
        {"error": "Not Found", "status_code": 404, "available_endpoints": AVAILABLE_ENDPOINTS},
        status_code=404,
    )


@app.get("/d/{code}")
async def challenge_page(code: str):
    """MR-14 — défi asynchrone : redirige vers daily avec le code."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"/daily.html?challenge={code}", status_code=302)


@app.get("/manifest.webmanifest")
async def web_manifest():
    page = FRONT / "manifest.webmanifest"
    if page.exists():
        return FileResponse(page, media_type="application/manifest+json")
    return JSONResponse({"name": "Music Refs", "start_url": "/daily.html", "display": "standalone"})


@app.get("/sw.js")
async def service_worker():
    page = FRONT / "sw.js"
    if page.exists():
        return FileResponse(page, media_type="application/javascript")
    return JSONResponse({"error": "Not Found"}, status_code=404)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):  # noqa: ARG001
    accept = (request.headers.get("accept") or "").lower()
    if "text/html" in accept:
        page = FRONT / "404.html"
        if page.exists():
            return HTMLResponse(page.read_text(encoding="utf-8"), status_code=404)
        return HTMLResponse(
            "<h1>404</h1><p>Oups ! Fausse Note</p><p><a href='/'>Accueil</a></p>",
            status_code=404,
        )
    return JSONResponse(
        {
            "error": "Not Found",
            "status_code": 404,
            "available_endpoints": AVAILABLE_ENDPOINTS,
        },
        status_code=404,
    )


if (FRONT / "src").is_dir():
    app.mount("/src", StaticFiles(directory=str(FRONT / "src")), name="src")
