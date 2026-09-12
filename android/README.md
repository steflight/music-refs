# Music Refs — Android (Kotlin + Jetpack Compose)

Client natif Android du monorepo Music Refs. Consomme l’API existante — aucun secret admin dans le binaire.

## Prérequis

- JDK 17+
- Android SDK (compileSdk 35, minSdk 26)
- Variable `ANDROID_HOME` (ou `local.properties` avec `sdk.dir=…`)

## Build

```bash
cd android
chmod +x gradlew
./gradlew :app:assembleDebug
./gradlew :app:testDebugUnitTest
```

APK debug : `app/build/outputs/apk/debug/app-debug.apk`

## Configuration API

Par défaut (BuildConfig) :

```
API_BASE_URL = https://music-refs-dev.kladriva.ca
```

Override debug possible via DataStore (`UserPreferences.setApiBaseOverride`) — pas d’UI v1, utile en tests.

## Deep links

| Schéma | Exemple |
|---|---|
| HTTPS | `https://music-refs-dev.kladriva.ca/party.html?code=ABCDEF` |
| Custom | `musicrefs://party?code=ABCDEF` |

Ouvre l’écran hub avec le code prérempli → saisie du prénom seulement.

## Périmètre v1

- Solo : catégorie, modes Normal / Facile, indices, score / streak / record
- Party : créer / rejoindre, lobby, polling 1,5 s, classement live, résultats
- Langue UI : français

Hors scope : admin, OAuth, push, audio/YouTube.

## Structure

```
app/src/main/java/ca/kladriva/musicrefs/
  data/api|model|prefs|repository/
  domain/game/          # GameEngine (port de gameService.js)
  ui/theme|home|solo|party|components/
```
