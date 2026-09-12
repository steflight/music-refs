# Backlog — Music Refs

Live : https://music-refs-dev.kladriva.ca · API v1.4 (Sprint 2 rétention)

| Statut | Signification |
|---|---|
| 🟢 | Fait |
| 🟡 | Planifié / en cours |
| ⚪ | Plus tard |
| 🔴 | Bloqué |

**Priorité** : boucle Refs du jour (MR-01…03, 06, 12) > security > mobile.

| Qui | Quoi |
|---|---|
| **Humains** | HUM-01 WhatsApp 14 j, Build in Public, go/no-go |
| **Agents / code** | MR-* / SEC-* / MOB-* |

Specs détaillées Given/When/Then : [`docs/backlog-traction-retention-v1.0.md`](docs/backlog-traction-retention-v1.0.md) (message produit « Traction & Rétention » v1.0, 2026-09-09) + `docs/conception/04-refs-du-jour-retention.md`.

---

## Tâches humaines

### [HUM-01] Test WhatsApp 5 refs × 3 groupes × 14 j — P0 humain
* **Statut** : 🟡  
* Critère : ≥ 5 personnes qui répondent spontanément 5 jours de suite.

### [HUM-02] Posts Build in Public — ⚪
### [HUM-03] Go/no-go après HUM-01 — ⚪

---

## Épic 1 — Refs du jour

### [MR-01] Sélection déterministe 5 refs / jour
* **Statut** : 🟢 Fait (2026-09-10)  
* `GET /api/music-refs/daily` · table `daily_sets` · seed Toronto · anti-repeat 90 j · sans réponses client.

### [MR-02] Parcours jeu quotidien
* **Statut** : 🟢 Fait (2026-09-10)  
* Page `/daily.html` · auto-next · état localStorage · CTA principal depuis l’accueil · pas de Reset.

### [MR-03] Écran de fin + bloc emoji partageable
* **Statut** : 🟢 Fait (2026-09-10)  
* Grille 🟩🟨⬛ · Web Share / copie / WhatsApp · `?ref=share`.

### [MR-04] Révélation + listen_url après partie
* **Statut** : 🟢 Fait (2026-09-10)  
* Après 5e : `reveals` dans `POST /result` + `GET /daily/reveal` · colonne `listen_url` · admin PATCH éditable.

### [MR-05] Archive éditions — ⚪ P2

---

## Épic 2 — Série quotidienne

### [MR-06] Compteur jours consécutifs + Combo renommé
* **Statut** : 🟢 Fait (2026-09-10)  
* Streak jours localStorage · HUD « Combo » sur infini · jalons 3/7/14/30/100.

### [MR-07] Gel de série
* **Statut** : 🟢 Fait (2026-09-10)  
* 1 gratuit, +1 / 7 j de série, max 2 · consommation auto si 1 jour manqué · HUD 🧊.

### [MR-08] Rappel push PWA
* **Statut** : 🟢 Fait (2026-09-12) — Web Push VAPID : `POST/DELETE /push/subscribe`, planificateur 19 h locale par fuseau, opt-in après la 2e partie, réglage, `sw.js` push/notificationclick, manifest + icônes. Clés dans `.env` (`scripts/gen_vapid.py`).

---

## Épic 3 — Feedback

### [MR-09] Rareté citations
* **Statut** : 🟢 Fait (2026-09-10)  
* `commune|rare|legendaire` · multiplicateurs 1 / 1.5 / 2 · style carte · set ≤1 légendaire ≥1 commune · 🟪 share.

### [MR-10] Micro-feedback (confettis, vibrate, sons)
* **Statut** : 🟢 Fait (2026-09-10)  
* Score roll, shake échec, confettis ≤800 ms (`ticks:40`), `prefers-reduced-motion`.

### [MR-11] Tolérance saisie / alias
* **Statut** : 🟢 Fait (renforcé 2026-09-10)  
* Articles FR/EN, Levenshtein ≤2 si ≥6 lettres, aliases — client `gameService.js` + serveur `daily.is_match`.

---

## Épic 4 — Social

### [MR-12] Pseudo léger sans compte
* **Statut** : 🟢 Fait (2026-09-10) — invite fin de daily + UUID local + POST result.

### [MR-13] Classement du jour
* **Statut** : 🟢 Fait (2026-09-10)  
* Top 10 UI écran de fin · départage score → hints → time_ms · API `/result` + `/leaderboard`.

### [MR-14] Défi asynchrone
* **Statut** : 🟢 Fait (2026-09-10, notification 2026-09-12)  
* `POST /daily/challenge` · `/d/<code>` · comparaison scores sur écran de fin · notification push au créateur « X a fait N/5 sur ton défi 😱 » (`challenge_code` dans `POST /result`, un envoi par défi).

### [MR-15] Profil culture
* **Statut** : 🟢 Fait (2026-09-12) — page `/profil` (alias `/profil.html`), historique local `mr:profile` (≤ 2 000 entrées, `src/services/profileStore.js`), barres SVG par catégorie, grade (seuils 40/70/90 %), meilleure série, légendaires ; PNG story 1080×1920 via canvas. Seuil : 20 citations répondues (daily + solo).
* Écart : agrégats 100 % locaux au navigateur (aucune API serveur) — un changement d'appareil repart de zéro.

---

## Épic 5 — Contenu communautaire

### [MR-16] Proposer punchline — 🟢 Fait (2026-09-12)
* `/proposer` · `POST /submissions` (doublon 409, lien d'écoute filtré, pseudo modéré, 10/jour) · admin « Propositions » approve/reject · +50 points + badge `contributeur` (`GET /players/{id}/rewards`) · « Proposée par » à la révélation.
### [MR-17] Vote 🔥/👎 — 🟢 Fait (2026-09-12)
* `POST /quotes/{id}/vote` (un vote/joueur, revotable, 403 si non jouée) · `GET /quotes/flagged` (≥ 30 votes, 👎 > 40 %) · admin « Signalées ».

---

## Épic 6 — Interface & mesure

### [MR-18] HUD centre + Reset caché
* **Statut** : 🟢 Fait
### [MR-19] Analytics événements
* **Statut** : 🟢 Fait (2026-09-12) — collecte `POST /events` sans cookie, `GET /stats` admin, tableau de bord `/stats.html` (DAU, rétention J1/J7/J30, % partagées, k-factor)

### [UX-04] Sons — 🟢 · [UX-05] Party mobile — 🟢 · [UX-03] Alias — 🟢

---

## Security by design

### [SEC-01] Play sans spoil — 🟢 Fait (2026-09-12) : catalogue public sans artiste/titre, `/options` pour le quiz, `/reveal` gardé
### [SEC-02] Score serveur — 🟢 Fait (2026-09-12) : `POST /quotes/{id}/answer`, demi-points artiste juste, `backend/scoring.py`
### [SEC-03] Party scores — 🟢 Fait (2026-09-12) : `/parties/{code}/answer` + `/skip`, `score` client ignoré
### [SEC-04] Rate-limit — 🟢 Fait (2026-09-12) : `backend/ratelimit.py`, `RATE_LIMIT_PER_MINUTE` (120), 429 français

---

## Mobile / autre

| ID | Statut |
|---|---|
| MOB-01 Android | 🟡 `android/` amorcé |
| MOB-01 iOS | ⚪ |
| MED-01 YouTube | ⚪ |
| ADM-01 Edit inline | ⚪ |

---

## Écarts vs spec v1.0 — audit du 2026-09-12 et correction (vague 1, même jour)

| Story | Critère de la spec | Audit matin | Après vague 1 |
|---|---|---|---|
| MR-04 / SEC-01 | Réponses accessibles seulement après la 5e citation | 🔴 `GET /daily/reveal` ouvert à tous | 🟢 403 sans résultat complet ; `/answer` ne révèle plus rien ; réponses suivies serveur (`daily_answers`) |
| MR-06 | Pastille « Série en danger » après 20 h | ⚪ | 🟢 `isStreakInDanger` + rendu ambre aria-live |
| MR-09 | Multiplicateurs ×1 / ×2 / ×3 | 🟡 ×1 / ×1,5 / ×2 | 🟢 ×1 / ×2 / ×3, indices 20/40/60, appliqué aussi au solo et au salon |
| MR-12 | Filtre de mots interdits sur le pseudo | ⚪ | 🟢 `backend/moderation.py` (FR/EN, accents, leet), 422 « Ce pseudo n'est pas autorisé » |
| MR-13 | Anti-triche : temps < 3 s/citation, score vérifié serveur | 🟡 | 🟢 400 « Temps trop court » / « Score incohérent… » ; score recalculé depuis les réponses serveur |
| MR-03 | `navigator.canShare`, lien du bloc sur l'origine courante | 🟡 | 🟢 |
| MR-19 | Tableau de bord DAU / rétention / k-factor | ⚪ | 🟢 `POST /events`, `GET /stats` (admin), page `/stats.html` |
| MR-13 | Onglet « Amis » du classement | ⚪ | ⚪ vague 3 |
| MR-14 | Notification « Karim a fait 5/5 » | ⚪ | 🟢 vague 2 (push au créateur) |

Preuve vague 1 (déploiement réel, joueur neuf) : `reveal` avant → 403, 5 × `/answer` sans fuite, `time_ms=1000` → 400, pseudo `m3rde` → 422, score 999 → 400, résultat honnête → 200 `complete:true` + 5 révélations, `reveal` après → 200, défi → code créé.

Tests vague 1 : pytest backend 74/74 ; vitest 40/40. Vague 2 (MR-08/14/15/16/17) : pytest 105/105 ; vitest 65/65 ; preuve live : soumission 201 → doublon 409 → approbation → +50 points/badge, vote sans jeu 403, abonnement push aller-retour, pages `/proposer` `/profil` en HTTPS 200 ; unittest racine 13/15 (2 échecs = chemins sandbox ADA codés en dur).

Hygiène : `certs/music-refs-dev.kladriva.ca.key` (auto-signée, QA) est versionnée depuis `436e34e` ; à sortir de l'historique avant tout passage public du dépôt.

---

## Hygiène

Mettre à jour ce fichier + `docs/projects-sync.md` à chaque livraison.
