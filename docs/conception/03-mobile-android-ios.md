# Conception — Apps mobiles natives (Android + iOS)

> Prompt de lancement · Music Refs · monorepo · 2026-09-08  
> À coller tel quel dans Cursor / ADA / un agent de dev.

**Référence web** : https://music-refs-dev.kladriva.ca  
**API** : `https://music-refs-dev.kladriva.ca` · Swagger `/docs` · Health `GET /health`  
**Contrat catégories/parties** : [02-categories-et-parties.md](02-categories-et-parties.md)

---

## Prompt — Music Refs mobile (Kotlin + Swift)

### Mission

Développer les clients mobiles **natifs** de **Music Refs** dans le **même dépôt** que le backend/web :

```
music-refs/
  backend/          # API FastAPI existante (ne pas la réécrire)
  android/          # Kotlin + Jetpack Compose
  ios/              # Swift + SwiftUI
  docs/             # ce contrat
  index.html, party.html, admin.html   # web (référence UX)
  src/services/gameService.js          # référence règles de jeu
```

Les apps **consomment** l’API existante. Elles ne remplacent pas le backend.  
Hors scope v1 mobile : admin, import paroles, token `X-Admin-Token`, audio/YouTube, comptes OAuth, push.

Langue UI : **français**.

Ordre de livraison recommandé :
1. **Android (Kotlin)** — MVP jouable solo + party  
2. **iOS (Swift/SwiftUI)** — même périmètre, même contrat API  
3. Parité visuelle / polish commun

---

### Produit (identique web)

Jeu : à partir d’une **punchline**, trouver **artiste** + **titre/moment**.

| Expérience | Comportement |
|---|---|
| **Solo** | Filtre catégorie optionnel, score/streak/record locaux, indices |
| **Partie amis** | Salon code, même catégorie + punchlines ordonnées, scores sync, classement live |

| Mode | UX |
|---|---|
| `classic` | Saisie libre artiste + titre (fuzzy match) |
| `easy` | Quiz : 4 artistes + 4 titres ; auto-valide dès les 2 choix |

---

### Stack

#### Android (`android/`)
- Kotlin, minSdk 26+, targetSdk courant  
- Jetpack Compose + Material 3  
- MVVM (ou MVI léger) + Navigation Compose  
- Retrofit + OkHttp + kotlinx.serialization (ou Moshi)  
- Coroutines + Flow · Hilt · DataStore  
- Deep links : `https://music-refs-dev.kladriva.ca/party.html?code=XXXXXX` + `musicrefs://party?code=XXXXXX`  
- Tests : `GameEngine` unitaire + MockWebServer

#### iOS (`ios/`)
- Swift 5.9+ · **SwiftUI** (natif, pas Flutter/RN/KMP obligatoire)  
- Architecture : MVVM + Observation / `@Observable`  
- Réseau : URLSession + async/await (ou Alamofire si besoin) + `Codable`  
- Persistence : `UserDefaults` / AppStorage (high score, prénom, API base debug)  
- Navigation : NavigationStack  
- Deep links : Universal Links / Associated Domains vers le même path `party.html?code=` + URL scheme `musicrefs://party?code=`  
- Tests : XCTest sur le moteur de jeu + URLProtocol mock  
- Cible : iOS 16+ (ou 17+ si `@Observable` simplifie)

#### Config commune
```
API_BASE_URL = https://music-refs-dev.kladriva.ca   # overridable en debug
```
Aucun secret admin dans les binaires.

---

### API joueur (contrat partagé)

#### Catalogue
| Méthode | Path |
|---|---|
| GET | `/api/music-refs/categories` |
| GET | `/api/music-refs/quotes?category_id=` |
| GET | `/api/music-refs/random` |
| GET | `/api/music-refs/quotes/{id}` |

#### Parties
| Méthode | Path | Body / notes |
|---|---|---|
| POST | `/api/music-refs/parties` | `{category_id, host_name, round_limit, mode}` · `mode` = `classic`\|`easy` |
| POST | `/api/music-refs/parties/join` | `{code, player_name}` |
| GET | `/api/music-refs/parties/{code}` | snapshot + `mode` + `players` |
| POST | `/api/music-refs/parties/{code}/start` | `{host_token}` |
| GET | `/api/music-refs/parties/{code}/quotes` | liste ordonnée figée |
| POST | `/api/music-refs/parties/{code}/score` | `{player_token, score, finished, progress}` · progress 1-based |

#### QuoteOut
```json
{
  "id": 1,
  "quote": "…",
  "artist": "…",
  "title": "…",
  "hints": { "year": "", "genre": "", "album": "", "initials": "" },
  "category_ids": [1]
}
```

#### Party snapshot (champs utiles)
- `code`, `status` ∈ `lobby` | `playing` | `finished`  
- `mode` ∈ `classic` | `easy`  
- `round_limit`, `quote_count`, `category`  
- `players[]` : `{id, name, is_host, score, finished, progress, total}`  
- `me` : `player_token`, `host_token` (création hôte)

Polling : **toutes les 1,5 s** en `lobby` / `playing` ; stop sur `finished` ou sortie d’écran.  
Erreurs : afficher `detail` FastAPI en snackbar / alert FR.

---

### Règles de jeu (porter fidèlement)

Référence : `src/services/gameService.js` (`GameEngine`, `isMatch`, `buildQuizChoices`).

Implémenter un **GameEngine** dans chaque plateforme (Kotlin + Swift) — même comportement :

**Normalisation / match**
- lower-case, NFD, strip accents, alphanum only  
- égalité normalisée OU substring si len≥3 OU Levenshtein ≤1 (court) / ≤2 (len>6)

**Score**
- Artiste : +100 · Titre : +100 · bonus full guess aligné sur le web  
- Indices solo : −20 par hint (`year`, `genre`, `album`, `initials`)  
- Streak + high score persistés  
- Party : ordre fixe, `advanceOrdered()`, sync score après validation / next / fin

**Mode easy**
- `buildQuizChoices(current, pool, count=4)` : 1 bonne + distracteurs uniques du pool, shuffle, fillers si pool petit  
- Auto-submit quand artiste + titre sélectionnés  
- Ne jamais révéler artiste/titre avant passer / full guess

---

### Écrans (parité Android ↔ iOS)

1. **Accueil** — brand MUSIC REFS · Jouer solo · Partie amis · Accueil toujours dispo ensuite  
2. **Solo setup** — catégorie (+ Toutes) · mode Normal/Facile · Commencer  
3. **Solo jeu** — HUD score/streak/record · punchline · indices · classic ou QCM · Valider · Suivant · Reset · **← Accueil**  
4. **Party hub** — créer (prénom, cat, mode, rounds 3–30) · rejoindre (prénom + code) · deep link = prénom seulement  
5. **Lobby** — code grand · cat + mode · joueurs · copier/partager lien · hôte lance · Accueil / Quitter  
6. **Party jeu** — score + progress · **classement live** (tri score puis progress, barre, highlight moi) · Accueil / Quitter · fin locale = attente autres  
7. **Résultats** — classement · Nouvelle partie · Accueil  

Back système : Accueil / confirmation si partie en cours.

---

### UX / design

- Dark `#0B0F19` · accents pink `#FF007F` · cyan `#00F0FF`  
- Display « gaming » + sans lisible (éviter Inter/Roboto/SF Pro « par défaut plat » sans identité)  
- Touch ≥ 48 dp / 44 pt · inputs ≥ 16 sp  
- Sticky top bar avec Accueil en jeu  
- Share sheet native (Android Intent / iOS UIActivityViewController)

---

### Structure dossiers suggérée

```
android/
  app/src/main/java/.../
    data/api/ repo/
    domain/game/     # GameEngine, normalize, quiz
    ui/theme/ home/ solo/ party/ components/

ios/
  MusicRefs/
    Data/API/ Repositories/
    Domain/Game/     # GameEngine, normalize, quiz
    UI/Theme/ Home/ Solo/ Party/ Components/
  MusicRefs.xcodeproj (ou .xcworkspace)
```

Option ultérieure (hors v1) : extraire les règles dans un module partagé (KMP / package de tests communs). **Pas requis** pour démarrer.

---

### Definition of Done

#### Android v1
1. `./gradlew :app:assembleDebug` OK  
2. Solo classic + easy + indices + record + Accueil  
3. Party create/join/deep link/start/quotes/score/live board/résultats  
4. Mode salon `easy` respecté  
5. Erreurs réseau non crashogènes  
6. README `android/` : build, `API_BASE_URL`, deep links  
7. Preuves : logcat ou captures des appels categories + party mode=easy  

#### iOS v1
1. Build Debug Xcode / `xcodebuild` OK (simulateur)  
2. Même périmètre fonctionnel qu’Android  
3. Deep link code → écran prénom  
4. README `ios/` : ouvrir le projet, scheme, Associated Domains  
5. Preuves : logs réseau ou captures équivalentes  

#### Commun
- Pas de secrets admin dans les apps  
- Pas d’endpoints admin  
- Doc monorepo à jour si écarts API découverts  

---

### Hors scope v1
- Admin / import / `X-Admin-Token`  
- Audio / YouTube  
- Flutter / React Native (choix = natif pur)  
- Comptes utilisateurs / OAuth / push  
- Scraping réseaux sociaux  

---

### Références code web
- Moteur : `src/services/gameService.js`  
- Party UI : `party.html`  
- Solo UI : `index.html`  
- Schemas : `backend/schemas.py`  
- Parties : [02-categories-et-parties.md](02-categories-et-parties.md)

### Comment démarrer (agent)
1. Scaffold `android/` (Compose + Retrofit health/categories)  
2. Porter `GameEngine` + Solo  
3. Party + polling + deep links  
4. Reproduire le même flux dans `ios/` (SwiftUI)  
5. Coller preuves DoD dans la réponse  

---

## Statut

| Plateforme | Statut |
|---|---|
| Android Kotlin | **à lancer** (prompt ci-dessus) |
| iOS Swift/SwiftUI | **à lancer** après ou en parallèle contrôlée d’Android |
| Monorepo | décidé — pas de repo mobile séparé pour v1 |
