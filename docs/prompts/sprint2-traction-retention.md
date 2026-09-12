# Prompt agent — Music Refs Sprint 2+ (suite Traction & Rétention)

Tu travailles dans `/home/steflight/qa-environment/music-refs` (live QA :8084, `music-refs-dev.kladriva.ca`).
Réponds et documente en **français**. Evidence over narrative : rebuild + curls collés.

## Déjà livré (Sprint 1) — NE PAS casser

- MR-01/02/03/06/12/18/19 (partiel) : `daily.html`, `backend/daily.py`, `backend/routes/daily.py`, tables `daily_sets`/`daily_results`, streak local, share emoji, analytics light, Combo rename, HUD.
- Mode infini (`index.html`) + Partie amis (`party.html`) doivent rester OK.

## Objectif de cette passe

Compléter dans l’ordre, sans demander de confirmation :

### P1 prioritaire
1. **MR-13** — Classement du jour : Top 10 visible sur l’écran de fin daily (déjà API `/result` + `/leaderboard`) ; départage score → hints → time.
2. **MR-11** — Vérifier/renforcer tolérance (Levenshtein ≤2 ≥6 lettres, articles, aliases) client **et** `daily.is_match` serveur ; demi-points artiste seul déjà partiel.
3. **MR-10** — Compléter feedback : score qui « roule », `prefers-reduced-motion`, shake échec, confettis ≤800 ms (déjà partiel).
4. **MR-04** — Après 5e citation seulement : révélation artiste+titre + `listen_url` optionnel (migration SQLite + admin éditable).
5. **MR-09** — Champ `rarity` commune|rare|légendaire ; multiplicateurs ; style carte ; contrainte set daily (≤1 légendaire, ≥1 commune) ; 🟪 dans le bloc share.
6. **MR-07** — Gel de série (1 gratuit, +1 / 7 jours série, max 2) consommation auto.

### Ensuite si le temps le permet
7. **MR-14** — Défi asynchrone `/d/<code>` (lien share, même set, comparaison).
8. **MR-08** — PWA + Web Push VAPID (rappel 19 h) — seulement si MR-07 OK.

### Hors scope cette passe
HUM-01 WhatsApp, MR-05 archive, MR-15 profil, MR-16/17 communauté, SEC-01 solo catalogue.

## Contraintes DoD workspace

- `docker compose up -d --build` prouvé
- `.env` non committé
- Mettre à jour `BACKLOG.md` + `docs/projects-sync.md` (statuts MR)
- Pas de commit git sauf si Stéphane le demande
- Ports : rester sur 8084, réseau `nginx-proxy-manager_default`

## Preuves minimales attendues en fin de passe

```bash
curl -sS 'http://127.0.0.1:8084/api/music-refs/daily?category=rap-francais' | head
curl -sS -X POST …/daily/answer … # match fuzzy
# UI : daily.html fin → Top 10 + révélation si MR-04
```

Lis `BACKLOG.md` et `docs/conception/04-refs-du-jour-retention.md` avant de coder.
