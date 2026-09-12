# Music Refs — Jeu des Punchlines & Citations

Application web : deviner artiste + titre à partir d’une punchline.

**Domaine** : `music-refs-dev.kladriva.ca`  
**API / frontend** : port hôte **8084** (conteneur `music-refs-api`)  
**ADA** reste sur **8082** — ne pas confondre.  
**Backlog** : [`BACKLOG.md`](BACKLOG.md) (security by design, mobile, etc.)

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
- Profil de culture musicale (MR-15) : `/profil` — agrégats locaux (`localStorage` clé `mr:profile`), visible à partir de 20 citations répondues, image story 1080×1920 téléchargeable
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

Import massif (QA) :

```bash
ADMIN_TOKEN="$(grep ADMIN_TOKEN .env | cut -d= -f2)" \
  python3 scripts/bulk_seed_lyrics.py --target 1000 --per-track 10
```

(Dadju, Singuila, M. Pokora, Booba, Orelsan, MHD + densification FR — admin peut corriger ensuite.)

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

## Mesure de la boucle (MR-19)

- Collecte sans cookie tiers : `src/services/analytics.js` (`track(nom, props)`) enfile les événements
  dans `localStorage` (`mr:analytics:queue`) et les envoie par lots (≤ 50) à `POST /api/music-refs/events`
  (`navigator.sendBeacon` quand la page se cache, sinon `fetch` keepalive, vidage toutes les 10 s).
  Identifiant joueur anonyme = l'UUID local du daily (`mr:player`, créé s'il manque) ; aucune donnée personnelle.
- Liste blanche serveur : `daily_started`, `daily_completed`, `share_clicked`, `share_landed`, `streak_milestone`,
  `challenge_created`, `challenge_accepted`, `notif_optin`, `quote_submitted` ; props ≤ 1 Ko ; horodatage serveur ;
  table `events` purgée à 180 jours au démarrage.
- Tableau de bord : http://127.0.0.1:8084/stats.html (token admin, mémorisé en `sessionStorage`), données via
  `GET /api/music-refs/stats?days=30` (X-Admin-Token). Jours calendaires America/Toronto.
  - DAU : joueurs distincts avec `daily_started` ou `daily_completed` le jour J.
  - Rétention J+n (n = 1, 7, 30) : cohorte = joueurs dont le premier `daily_completed` tombe dans la fenêtre et dont
    J+n est passé ; `pct` = % ayant un `daily_completed` exactement à J+n ; `pct_or_later` = à J+n ou plus tard.
  - % parties partagées = (joueur, jour) avec `share_clicked` ÷ (joueur, jour) avec `daily_completed`.
  - k-factor ≈ `share_landed` ÷ `daily_completed` (comptes bruts sur la fenêtre).

## Rappel quotidien Web Push (MR-08) & notification de défi (MR-14)

PWA installable (`manifest.webmanifest`, icônes `icons/`, `sw.js`) + Web Push VAPID.

- Variables : `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` (mailto:), `PUSH_REMINDER_HOUR`
  (défaut 19), `PUSH_SCHEDULER_ENABLED` (défaut 1). Générer les clés : `python3 scripts/gen_vapid.py --append .env`.
  Sans clés, l'API démarre normalement, push désactivé (log `VAPID … absentes`).
- API : `GET /api/music-refs/push/public-key` · `POST /api/music-refs/push/subscribe`
  `{player_id, subscription{endpoint, keys{p256dh, auth}}, tz, streak?}` · `DELETE /api/music-refs/push/subscribe {endpoint}`.
  Table `push_subscriptions` (un abonnement par endpoint, fuseau IANA du joueur).
- Planificateur (`backend/push.py`) : tâche asyncio au démarrage, un tick par minute ; à 19 h **locale**
  (fuseau `tz`), si le joueur n'a pas de résultat complet du jour (date Toronto), envoi de
  « 🔥 Ta série de N jours expire dans 5 h. Les refs du jour t'attendent. » (sans N si série inconnue),
  une fois par jour (`last_sent_day`). Endpoint 404/410 → abonnement supprimé.
- MR-14 : quand l'ami termine un défi (`POST /daily/result` avec `challenge_code`), le créateur abonné
  reçoit « <pseudo> a fait X/5 sur ton défi 😱 » (un seul envoi par défi, colonne `notified_at`).
- Front (`daily.html`) : bloc « Reçois un rappel à 19 h si tu n'as pas joué » sous l'écran de fin,
  proposé seulement après la 2e partie terminée ; réglage « Rappel quotidien : activé/désactivé »
  persistant (`mr:push`) ; masqué si `Notification`/`PushManager` absents (iOS Safari non installé).
- Tests : `cd backend && python3 -m pytest tests/test_push.py -q` (envoi mocké).

## Contrats d'API — sécurité (SEC-01 → SEC-04, 2026-09-12)

| Route | Comportement |
|---|---|
| `GET /api/music-refs/quotes`, `/random`, `/quotes/{id}` | Sans `X-Admin-Token` : `{id, quote, hints, rarity, category_ids}` (plus d'artiste/titre/lien). Avec token : complet. |
| `GET /api/music-refs/quotes/{id}/options` | Propositions mélangées pour le quiz (`artists[]`, `titles[]`). |
| `POST /api/music-refs/quotes/{id}/answer` | `{artist, title, hints_used, mode}` → verdict serveur `{artist_ok, title_ok, fully_correct, points, half_points, message, reveal}`. |
| `POST /api/music-refs/quotes/{id}/reveal` | Abandon : renvoie artiste, titre, lien d'écoute. |
| `POST /api/music-refs/parties/{code}/answer`, `/skip` | Réponse vérifiée serveur ; `/score` ignore désormais tout score client. |
| `POST /api/music-refs/daily/answer` | Requiert `player_id` ; `skip:true` pour passer ; renvoie `score_delta`, `cell`, jamais la réponse. |
| `GET /api/music-refs/daily/reveal?player_id=` | 403 tant que le joueur n'a pas joué les 5 citations. |
| `POST /api/music-refs/daily/result` | Score recalculé serveur (400 si incohérent ou < 3 s/citation), pseudo modéré (422). |
| Toute écriture publique | 429 au-delà de `RATE_LIMIT_PER_MINUTE` (défaut 120) par IP. |

Barème (`backend/scoring.py`) : artiste 100 + titre 100 + 50 si complet, −20 par indice, × rareté (commune 1, rare 2, légendaire 3).

## Contenu communautaire (MR-16 / MR-17, 2026-09-12)

| Route | Auth | Rôle |
|---|---|---|
| `GET /proposer` | — | Formulaire « Proposer une punchline » |
| `POST /api/music-refs/submissions` | public | Proposition → `pending` ; 409 doublon, 422 validation/pseudo, 429 au-delà de 10/jour |
| `GET /api/music-refs/submissions?status=` | admin | Liste + compteurs (onglet « Propositions » de l'admin) |
| `POST /api/music-refs/submissions/{id}/approve` · `/reject` | admin | Approbation crée la citation, +50 points et badge `contributeur` |
| `GET /api/music-refs/players/{player_id}/rewards` | public | `{points, badges[]}` |
| `POST /api/music-refs/quotes/{id}/vote` | public | `{player_id, value: 1|-1}`, un vote par joueur, 403 si la citation n'a pas été jouée |
| `GET /api/music-refs/quotes/flagged` | admin | Citations ≥ 30 votes et 👎 > 40 % (onglet « Signalées ») |
