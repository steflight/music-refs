# Statut d’implémentation — plan « API lyrics sans IA »

Réponse courte : **oui**, le plan est présent dans la codebase. Détail ci-dessous.

| Élément du plan | Présent ? | Emplacement |
|---|---|---|
| Backend FastAPI | oui | `backend/main.py` |
| Health `/health` | oui | `backend/main.py` |
| SQLite + seed | oui | `backend/db.py`, `backend/seed_quotes.json`, volume `backend/data/` |
| Provider LRCLIB | oui | `backend/providers/lrclib.py` |
| Provider iTunes | oui | `backend/providers/itunes.py` |
| Fallback MusicBrainz | oui (extra) | `backend/providers/musicbrainz.py` |
| `GET /api/music-refs/quotes` | oui | `backend/routes/quotes.py` |
| `GET /api/music-refs/random` | oui | idem |
| `POST /api/music-refs/import` | oui | idem |
| `POST /api/music-refs/quotes` | oui | idem |
| `DELETE /api/music-refs/quotes/{id}` | oui | idem |
| Auth `X-Admin-Token` | oui | `backend/auth.py`, `.env` |
| `admin.html` import | oui | `admin.html` |
| `admin.html` catalogue réponses | oui (extra) | `admin.html` |
| Port 8084 + compose | oui | `docker-compose.yml` |
| Proxy ≠ ADA 8082 | oui | `nginx.conf`, NPM, `infra-reverse-proxy.md`, `CLAUDE.md` |
| Frontend charge l’API | oui | `src/services/gameService.js`, `index.html`, `src/App.jsx` |
| Fallback `quotes.js` | oui | `loadQuotesFromApi()` |
| README | oui | `README.md` |
| Doc conception versionnée | oui | `docs/conception/` |

## Todos du plan (tous completed)

1. backend-fastapi  
2. providers  
3. admin-auth  
4. compose-port  
5. frontend-api  
6. prove-dod  

## Hors scope (non fait, volontairement)

- Lookup punchline → artiste via LLM  
- Agent ADA de chasse  
- Cadre légal paroles en prod publique  
- Lien YouTube en arrière-plan (reporté)

## Livraison v1.2 — catégories & parties

Voir [02-categories-et-parties.md](02-categories-et-parties.md) — **implémenté** (2026-09-07).
