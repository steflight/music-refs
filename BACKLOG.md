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
* **Statut** : 🟡 Partiel — `manifest.webmanifest` + `sw.js` (cache shell) ; **pas** de Web Push VAPID 19 h.

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
* **Statut** : 🟢 Fait (2026-09-10)  
* `POST /daily/challenge` · `/d/<code>` · comparaison scores sur écran de fin.

### [MR-15] Profil culture — ⚪ P2

---

## Épic 5 — Contenu communautaire

### [MR-16] Proposer punchline — ⚪ P2
### [MR-17] Vote 🔥/👎 — ⚪ P2

---

## Épic 6 — Interface & mesure

### [MR-18] HUD centre + Reset caché
* **Statut** : 🟢 Fait
### [MR-19] Analytics événements
* **Statut** : 🟢 Fait (light) — `src/services/analytics.js` queue local + plausible hook ; dashboard externe ⚪

### [UX-04] Sons — 🟢 · [UX-05] Party mobile — 🟢 · [UX-03] Alias — 🟢

---

## Security by design

### [SEC-01] Play sans spoil — 🟡 Partiel (daily OK ; catalogue solo encore exposé)
### [SEC-02] Score serveur — 🟡 Partiel (daily answer serveur ; solo client)
### [SEC-03] Party scores — ⚪
### [SEC-04] Rate-limit — ⚪

---

## Mobile / autre

| ID | Statut |
|---|---|
| MOB-01 Android | 🟡 `android/` amorcé |
| MOB-01 iOS | ⚪ |
| MED-01 YouTube | ⚪ |
| ADM-01 Edit inline | ⚪ |

---

## Écarts constatés vs spec v1.0 (audit du 2026-09-12)

Vérifié sur le déploiement live (image = sources, `/health` v1.4.0). Les stories 🟢 ci-dessus sont livrées, avec ces écarts précis :

| Story | Critère de la spec | État | Suite |
|---|---|---|---|
| MR-04 / SEC-01 | Réponses accessibles **seulement après** la 5e citation | 🔴 `GET /daily/reveal` renvoie artiste + titre à n'importe quel `player_id`, même sans résultat enregistré | Exiger un `daily_results` complet pour ce joueur (ou n'exposer `reveals` que dans la réponse de `POST /result`) |
| MR-06 | Pastille « Série en danger » après 20 h locale si set non commencé | ⚪ Non implémenté | Petit ajout front (`dailyStore.js` + en-tête `daily.html`) |
| MR-09 | Multiplicateurs ×1 / ×2 / ×3 | 🟡 Implémenté ×1 / ×1.5 / ×2 (`backend/daily.py`) | Décision produit : aligner sur la spec ou entériner la version douce |
| MR-12 | Filtre de mots interdits sur le pseudo | ⚪ Absent (3–16 caractères seulement) | Liste courte FR/EN côté serveur dans `POST /result` |
| MR-03 | `navigator.canShare` avant `navigator.share` | 🟡 `navigator.share` testé directement (fonctionne, moins robuste) | Cosmétique |
| MR-03 | Lien du bloc `music-refs.kladriva.ca` | 🟡 Lien QA `music-refs-dev.kladriva.ca/daily.html?ref=share` en dur | Basculer en `location.origin` au passage en prod |
| MR-13 | Onglet « Amis » du classement | ⚪ Non implémenté | Dépend d'un lien joueur ↔ salon |
| MR-14 | Notification « Karim a fait 5/5 » | ⚪ Dépend de MR-08 (Web Push) | Sprint 3 |
| MR-19 | Tableau de bord DAU / rétention / k-factor | ⚪ Événements émis, pas de dashboard | Brancher Plausible ou Umami |

Tests (2026-09-12) : `vitest` 7/7 après mise à jour du test de normalisation (MR-11) ; `unittest` 13/15 — les 2 échecs sont des chemins de sandbox ADA codés en dur (`/workspace/music-refs/...`), pas des régressions.

Hygiène : `certs/music-refs-dev.kladriva.ca.key` (auto-signée, QA) est versionnée depuis `436e34e` ; à sortir de l'historique avant tout passage public du dépôt.

---

## Hygiène

Mettre à jour ce fichier + `docs/projects-sync.md` à chaque livraison.
