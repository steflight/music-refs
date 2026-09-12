"""SEC-04 — Limitation de débit simple, en mémoire, par IP.

Middleware Starlette : fenêtre glissante de 60 s sur les requêtes d'écriture
publiques (POST/PUT/PATCH/DELETE). Exemptions : /health, les méthodes de
lecture, et les requêtes portant un `X-Admin-Token` valide.

Derrière nginx-proxy-manager, l'IP réelle est le premier élément de
`X-Forwarded-For` (sinon `X-Real-IP`, sinon l'adresse de connexion).

Configuration : variable d'environnement `RATE_LIMIT_PER_MINUTE` (défaut 120,
0 = désactivé) — lue via `config.Settings`.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import get_settings

WINDOW_SECONDS = 60
EXEMPT_PATHS = {"/health"}
LIMITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MESSAGE_429 = "Trop de requêtes. Réessayez dans une minute."

# Surcharge (tests / exploitation) : None → valeur de config.
_limit_override: int | None = None
_buckets: dict[str, deque[float]] = {}
_lock = threading.Lock()
_last_sweep = 0.0


def set_limit(limit: int | None) -> None:
    """Fixe la limite courante (None = revenir à la configuration)."""
    global _limit_override
    _limit_override = limit


def current_limit() -> int:
    if _limit_override is not None:
        return int(_limit_override)
    return int(get_settings().rate_limit_per_minute)


def reset() -> None:
    """Vide les compteurs (utile entre deux tests)."""
    with _lock:
        _buckets.clear()


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
        if first:
            return first
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _is_admin(request: Request) -> bool:
    token = request.headers.get("x-admin-token")
    expected = get_settings().admin_token
    return bool(token) and token == expected


def _hit(ip: str, limit: int, now: float) -> tuple[bool, int]:
    """Enregistre une requête ; renvoie (autorisé, secondes avant réouverture)."""
    global _last_sweep
    with _lock:
        if now - _last_sweep > WINDOW_SECONDS:
            for key in [k for k, dq in _buckets.items() if not dq or now - dq[0] > WINDOW_SECONDS]:
                _buckets.pop(key, None)
            _last_sweep = now
        dq = _buckets.setdefault(ip, deque())
        while dq and now - dq[0] > WINDOW_SECONDS:
            dq.popleft()
        if len(dq) >= limit:
            retry = int(WINDOW_SECONDS - (now - dq[0])) + 1
            return False, max(1, retry)
        dq.append(now)
        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method not in LIMITED_METHODS or request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        limit = current_limit()
        if limit <= 0 or _is_admin(request):
            return await call_next(request)
        allowed, retry_after = _hit(client_ip(request), limit, time.monotonic())
        if not allowed:
            return JSONResponse(
                {"detail": MESSAGE_429, "retry_after": retry_after},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
