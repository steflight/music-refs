<!-- projects-sync: v1 -->

# Music Refs — snapshot Projects

## Meta
- slug: music-refs
- name: Music Refs — Jeu des punchlines
- key_prefix: MR
- color: #FF007F

## Description

Music Refs est un jeu web (et bientôt mobile) où l’on devine **artiste + titre** à partir d’une punchline. Déployé en QA sur `music-refs-dev.kladriva.ca` (port hôte **8084**, API FastAPI + SQLite + front HTML).

État actuel : catalogue ~**2274** punchlines, solo + **parties amis**, admin. **Refs du jour** + Sprint 2 rétention en QA (édition depuis 2026-09-10) : Top 10, révélation/`listen_url`, rareté, gel de série, défi `/d/<code>`, PWA shell. Charte néon rose/cyan.

Priorité produit : Web Push VAPID (MR-08 suite), archive (MR-05), SEC-01 solo catalogue. Mobile Kotlin/SwiftUI monorepo (`android/` amorcé). Sprint 1+2 committés le 2026-09-12 ; écarts vs spec listés dans `BACKLOG.md`.

## Docs

### Contexte agents
<!-- kind: context ; agents: true -->

- **Live** : https://music-refs-dev.kladriva.ca — API `/docs`, health `/health`, admin `/admin.html`
- **Backlog canonique** : `BACKLOG.md` (HUM / RET / UX / SEC / MOB) — mettre à jour à chaque livraison
- **Conception** : `docs/conception/01-api-lyrics-sans-ia.md`, `02-categories-et-parties.md`, `03-mobile-android-ios.md`, `04-refs-du-jour-retention.md`
- **Procédures** (sans secret) : `docs/procedures.md` — token QA dans `ACCES-ET-PROCEDURES.md` (gitignoré)
- **Règle** : tâches **HUM-*** = humains seulement (WhatsApp 14 j avant de sur-coder le daily)
- **Stack** : FastAPI `backend/`, front `index.html` / `party.html` / `admin.html`, moteur `src/services/gameService.js`, seed `scripts/bulk_seed_lyrics.py`, compose port 8084
- **Ne pas** committer `.env` / `backend/data/*.db` / secrets admin
- **Priorité code** : MR-08 Push VAPID · SEC-01 solo · MOB Android · HUM-01 en parallèle humain
- **Prompt suite** : `docs/prompts/sprint2-traction-retention.md` (Sprint 2 code livré 2026-09-10)

### Liens utiles
<!-- kind: link -->
- Prod QA : https://music-refs-dev.kladriva.ca
- Swagger : https://music-refs-dev.kladriva.ca/docs
- Backlog : `BACKLOG.md`

## Backlog

### Issue: Mettre en place l’API FastAPI quotes et import LRCLIB
- status: done
- type: feature
- priority: p1
- tags: api, lyrics, livré

Backend FastAPI, SQLite, providers LRCLIB/iTunes/MusicBrainz, auth `X-Admin-Token`, compose 8084.  
Preuves : commit `e169144` (2026-09-08), `backend/`, `docker-compose.yml`.

### Issue: Livrer catégories, parties amis et mode quiz
- status: done
- type: feature
- priority: p1
- tags: party, quiz, livré

Salons code, scores sync, classement live, mode `classic`/`easy`, filtre solo.  
Preuves : commit `8877f0e` (2026-09-08), `party.html`, `backend/routes/parties.py`.

### Issue: Documenter conception API, parties et prompt mobile
- status: done
- type: tache
- priority: p2
- tags: docs, livré

Docs conception + procédures + prompt Android/iOS monorepo.  
Preuves : commits `8a5c6f5`, `c1dc0bd` (2026-09-08), `docs/conception/`.

### Issue: Peupler le catalogue au-delà de 1000 punchlines
- status: done
- type: tache
- priority: p2
- tags: contenu, seed, livré

Seed massif (Dadju, Booba, Orelsan, MHD, Pokora, gospel, Tayc, Sexion…).  
Preuves : `scripts/bulk_seed_lyrics.py`, API ~2274 quotes (QA 2026-09-09). Catégorie Gospel créée.

### Issue: Centrer le HUD et masquer le Reset
- status: done
- type: tache
- priority: p2
- tags: ux, rétention, livré

Score/série/record en bandeau émotionnel ; Reset en lien footer.  
Preuves : `index.html` (working tree 2026-09-09), BACKLOG UX-01.

### Issue: Ajouter confettis de victoire
- status: done
- type: tache
- priority: p2
- tags: ux, livré

Confettis + pop carte au full guess (solo + party).  
Preuves : `index.html`, `party.html`, canvas-confetti CDN, BACKLOG UX-02.

### Issue: Accepter les orthographes artistes (M. Pokora / Matt Pokora)
- status: done
- type: bug
- priority: p1
- tags: matching, livré

`isMatch` : alias, initiales, nom seul, typos.  
Preuves : `src/services/gameService.js`, BACKLOG UX-03.

### Issue: Rendre le setup party mobile-friendly
- status: done
- type: tache
- priority: p1
- tags: mobile, party, livré

Onglets Créer/Rejoindre, champs 52px, −/+ rounds.  
Preuves : `party.html`, BACKLOG UX-05.

### Issue: Créer le backlog rétention et security by design
- status: done
- type: tache
- priority: p2
- tags: docs, produit, livré

`BACKLOG.md` + conception Refs du jour ; séparation HUM vs agents.  
Preuves : `BACKLOG.md`, `docs/conception/04-refs-du-jour-retention.md` (non encore tous commités).

### Issue: Tester manuellement 5 refs du jour sur WhatsApp
- status: todo
- type: tache
- priority: p0
- tags: humain, rétention, HUM-01

14 jours × 3 groupes ; critère ≥5 répondants spontanés 5 j de suite. **Hors agents.** Peut tourner en parallèle du Sprint 1 déjà shippé.

### Issue: Implémenter le mode Refs du jour
- status: done
- type: feature
- priority: p1
- tags: rétention, MR-01, MR-02, livré

`GET /api/music-refs/daily`, table `daily_sets`, `daily.html`, auto-next, localStorage.  
Preuves QA 2026-09-10 : set identique, pas d’artiste dans le payload play, `/daily.html` 200.

### Issue: Ajouter écran de fin et grille emoji partageable
- status: done
- type: feature
- priority: p1
- tags: rétention, share, MR-03, livré

Bloc 🟩🟨⬛ + Web Share / copie / WhatsApp + `?ref=share`.

### Issue: Streak quotidienne en jours (sans gel)
- status: done
- type: feature
- priority: p1
- tags: rétention, MR-06, livré

Compteur jours + jalons ; Combo renommé sur mode infini. Gel = MR-07 restant.

### Issue: Pseudo léger + analytics boucle daily
- status: done
- type: feature
- priority: p1
- tags: MR-12, MR-19, livré

UUID + pseudo local ; `src/services/analytics.js` (événements queue / Plausible hook).

### Issue: Classement du jour (Top 10 UI)
- status: done
- type: feature
- priority: p1
- tags: MR-13, livré

Top 10 écran de fin daily ; départage score → hints → time.  
Preuves QA 2026-09-10 : `POST /result` + `GET /leaderboard`, `daily.html#leaderboard-list`.

### Issue: Gel de série + rareté + révélation listen_url
- status: done
- type: feature
- priority: p1
- tags: MR-07, MR-09, MR-04, livré

Gel (1 gratuit, +1/7j, max 2) ; rarity + multiplicateurs + 🟪 ; reveals + `listen_url` admin PATCH.  
Preuves : answer légendaire ×2 = 500 pts ; `GET /daily/reveal` ; colonnes SQLite.

### Issue: Défi asynchrone + PWA shell
- status: done
- type: feature
- priority: p1
- tags: MR-14, MR-08, livré

`/d/<code>`, `POST /daily/challenge` ; manifest + sw.js. Push VAPID 19 h encore ouvert (MR-08 suite).

### Issue: Ajouter les sons de feedback avec mute
- status: done
- type: feature
- priority: p2
- tags: ux, audio, UX-04, livré

SFX succès / partiel / erreur / streak via Web Audio ; toggle 🔊 ; solo + party.  
Preuves : `src/services/sfx.js`, `index.html`, `party.html` (2026-09-10).

### Issue: Ne plus exposer artiste et titre au client avant validation
- status: todo
- type: feature
- priority: p1
- tags: security, SEC-01

Endpoint play sans réponses ; révélation post-validate. Critique avant classement daily.

### Issue: Valider et scorer côté serveur
- status: todo
- type: feature
- priority: p1
- tags: security, SEC-02

Porter fuzzy match + quiz easy côté API. Dépend SEC-01.

### Issue: Rendre les scores party non falsifiables
- status: todo
- type: feature
- priority: p1
- tags: security, SEC-03

Ignorer score client ; dériver des validations. Dépend SEC-02.

### Issue: Poursuivre l’app Android Kotlin Compose
- status: in_progress
- type: feature
- priority: p2
- tags: mobile, MOB-01

Monorepo `android/` amorcé ; parité solo/party avec API. Prompt `docs/conception/03-mobile-android-ios.md`.

### Issue: Amorcer l’app iOS SwiftUI
- status: todo
- type: feature
- priority: p2
- tags: mobile, MOB-01

Même contrat API que Android ; dossier `ios/` à créer.

### Issue: Publier les posts Build in Public rétention
- status: todo
- type: tache
- priority: p3
- tags: humain, HUM-02

Draft déjà dans le fil produit. **Hors agents.**
