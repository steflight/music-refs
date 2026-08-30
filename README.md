# Music Refs - Le Jeu des Punchlines & Citations (Task #4)

**Music Refs** est une application web moderne et interactive permettant aux passionnés de musique de deviner des artistes et des chansons à partir de citations et punchlines tirées au sort.

---

## 🎯 User Stories Implémentées

### 1. Affichage aléatoire de punchlines et citations
- **Fichiers** : [`src/data/quotes.js`](src/data/quotes.js), [`src/services/gameService.js`](src/services/gameService.js), [`src/components/QuoteCard.jsx`](src/components/QuoteCard.jsx), [`index.html`](index.html)
- **Description** :
  - Base de données riche de citations musicales variées (Rap Français, Variété, Pop, Electro, Rock).
  - Sélection tirée au sort sans répétition jusqu'à épuisement du catalogue.
  - Masquage initial de l'artiste et du titre avec affichage mis en valeur dans une carte stylisée.

### 2. Saisie et validation de la réponse
- **Fichiers** : [`src/services/gameService.js`](src/services/gameService.js), [`src/components/AnswerForm.jsx`](src/components/AnswerForm.jsx), [`index.html`](index.html)
- **Description** :
  - Champs de saisie dédiés pour l'artiste/groupe et le titre de la chanson.
  - Moteur de comparaison tolérant : suppression des accents, de la casse, des espaces superflus et de la ponctuation, avec support de la recherche approximative (Levenshtein).
  - Validation instantanée avec retour visuel (notifications, verrouillage progressif des champs trouvés).

### 3. Système d'affichage d'indices
- **Fichiers** : [`src/components/HintSystem.jsx`](src/components/HintSystem.jsx), [`src/services/gameService.js`](src/services/gameService.js), [`index.html`](index.html)
- **Description** :
  - 4 indices débloquables :
    1. 📅 **Année de sortie**
    2. 🎵 **Genre musical**
    3. 💿 **Album / Projet**
    4. 🔤 **Initiales de l'artiste et du titre**
  - Pénalité dynamique de -20 points par indice révélé.

### 4. Calcul et suivi du score
- **Fichiers** : [`src/components/ScoreBoard.jsx`](src/components/ScoreBoard.jsx), [`src/services/gameService.js`](src/services/gameService.js)
- **Description** :
  - Actualisation du score en temps réel (+100 pts par élément trouvé, bonus combo +50 pts).
  - Multiplicateur de série (Streak 🔥) pour les réponses consécutives exactes.
  - Sauvegarde du meilleur score (High Score) dans le `localStorage`.

### 5. Progression et rejouabilité
- **Fichiers** : [`src/components/GameControls.jsx`](src/components/GameControls.jsx), [`src/services/gameService.js`](src/services/gameService.js)
- **Description** :
  - Bouton **Citation suivante / Passer** pour passer une devinette difficile et afficher la réponse.
  - Bouton **Réinitialiser la partie** avec modal de confirmation pour remettre à zéro score et série.

### 6. Interface moderne et dynamique
- **Fichiers** : [`index.html`](index.html), [`src/App.jsx`](src/App.jsx)
- **Description** :
  - Design moderne glassmorphism avec thème néon sombre (gradients violet/cyan/rose).
  - Animations fluides (shake en cas d'erreur, animation vinyle, apparitions douces).
  - Design responsive adapté aux téléphones, tablettes et écrans d'ordinateurs.

---

## 🧪 Suite de Tests Automated

- **Tests unitaires et d'intégration Frontend (JavaScript / Vitest)** : [`src/services/GameService.test.js`](src/services/GameService.test.js)
  - Validation de la normalisation de chaînes et de la tolérance aux fautes.
  - Tests du moteur de jeu : tirage aléatoire, gestion des indices, calcul du score et réinitialisation.
- **Tests unitaires et d'intégration Backend (Python unittest)** : [`tests/test_music_refs.py`](tests/test_music_refs.py)
  - Vérification complète des 6 user stories en Python (`python3 -m unittest /app/music-refs/tests/test_music_refs.py`).

---

## 📌 Informations Git & Branche

- **Branche de feature** : `ada-feature-4`
- **Remote Origin** : `origin`
- **Message de commit** : `feat: implement user stories for task #4`
