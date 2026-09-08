# Music Refs — Jeu des Punchlines & Citations

Application web : deviner artiste + titre à partir d’une punchline.

**Domaine** : `music-refs-dev.kladriva.ca`  
**API / frontend** : port hôte **8084** (conteneur `music-refs-api`)  
**ADA** reste sur **8082** — ne pas confondre.

## Démarrage

```bash
cd /home/steflight/qa-environment/music-refs
cp .env.example .env   # si besoin, puis définir ADMIN_TOKEN
docker compose up -d --build
```

Preuves :

```bash
curl -sS http://127.0.0.1:8084/health
curl -sS http://127.0.0.1:8084/api/music-refs/quotes | head
```

Swagger : http://127.0.0.1:8084/docs  
Admin (catalogue + import) : http://127.0.0.1:8084/admin.html  

**Accès & procédures (token, NPM, CLI)** :  
- Versionnées (sans secret) : [`docs/procedures.md`](docs/procedures.md)  
- Conception / plan : [`docs/conception/`](docs/conception/)  
- Token QA en clair : [`ACCES-ET-PROCEDURES.md`](ACCES-ET-PROCEDURES.md) (local, non versionné)

## Catégories & parties amis

- Solo : filtre catégorie en haut de `/`
- Salon : `/party.html` (code à partager)
- Admin : créer catégories + cocher punchlines → Assigner
- Conception : [docs/conception/02-categories-et-parties.md](docs/conception/02-categories-et-parties.md)

```bash
curl -sS http://127.0.0.1:8084/api/music-refs/categories | jq .
curl -sS -X POST http://127.0.0.1:8084/api/music-refs/parties \
  -H 'Content-Type: application/json' \
  -d '{"category_id":1,"host_name":"Alex","round_limit":5}' | jq .
```

## Compte / secret admin

| Clé | Usage |
|---|---|
| `ADMIN_TOKEN` (fichier `.env`) | Header `X-Admin-Token` pour `POST /import`, `POST /quotes`, `DELETE` |

Le token généré pour cet environnement est documenté dans `ACCES-ET-PROCEDURES.md` et `.env` (non commités).

L’admin permet de **voir les réponses** (artiste + titre) pour chaque punchline dans le catalogue, pas seulement d’importer.

## Peupler les punchlines (sans IA)

1. Ouvrir `/admin.html`, coller le token.
2. Saisir **artiste + titre** (ex. Damso / Macarena).
3. L’API appelle **LRCLIB** (paroles) + **iTunes** (année / album / genre).
4. Cocher les lignes → Enregistrer → elles apparaissent dans `GET /api/music-refs/quotes`.

CLI :

```bash
TOKEN="$(grep ADMIN_TOKEN .env | cut -d= -f2)"

curl -sS -X POST http://127.0.0.1:8084/api/music-refs/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $TOKEN" \
  -d '{"artist":"Damso","title":"Macarena"}'

curl -sS -X POST http://127.0.0.1:8084/api/music-refs/quotes \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $TOKEN" \
  -d '{"quotes":[{"quote":"…","artist":"Damso","title":"Macarena","hints":{"year":"2017","genre":"Hip-Hop/Rap","album":"Ipséité","initials":"…"}}]}'
```

## Endpoints

| Méthode | Chemin | Auth |
|---|---|---|
| GET | `/health` | non |
| GET | `/api/music-refs/quotes` | non |
| GET | `/api/music-refs/random` | non |
| POST | `/api/music-refs/import` | `X-Admin-Token` |
| POST | `/api/music-refs/quotes` | `X-Admin-Token` |
| DELETE | `/api/music-refs/quotes/{id}` | `X-Admin-Token` |

Stockage : SQLite `backend/data/quotes.db` (seed initial depuis `backend/seed_quotes.json`).

## Routage NPM

Proposer / vérifier dans nginx-proxy-manager :

- Domaine : `music-refs-dev.kladriva.ca`
- Forward : `172.17.0.1:8084` (plus `8082`)

## Stack SSL historique

Scripts `scripts/cert_manager.py`, `scripts/ssl_monitor.py` et `certs/` : tâches ADA #6 (certifs auto-signés SNI). En prod via NPM, Let’s Encrypt côté NPM.
