# Music Refs - Le Jeu des Punchlines & Citations (Task #5)

**Music Refs** est une application web moderne et interactive permettant aux passionnés de musique de deviner des artistes et des chansons à partir de citations et punchlines tirées au sort.

---

## 🎯 User Stories Implémentées (Task #5 - Routage, Reverse Proxy & 404)

### 1. Routage de la Racine (`/`) vers l'Interface Web Frontend
- **Fichiers** : [`index.html`](index.html), [`/app/main.py`](/app/main.py)
- **Description** :
  - Les requêtes HTTP navigateur vers `http://music-refs-dev.kladriva.ca/` (URL racine `/`) servent directement l'interface SPA `index.html` au lieu de renvoyer une erreur JSON 404 brute.

### 2. Configuration Reverse Proxy et Serveur de Fichiers Statiques
- **Fichiers** : [`nginx.conf`](nginx.conf), [`/workspace/nginx-proxy-manager/migrate_hosts.py`](/workspace/nginx-proxy-manager/migrate_hosts.py)
- **Description** :
  - Configuration Nginx reverse proxy et serveur de fichiers statiques permettant de servir les assets de l'application et de rediriger les requêtes vers l'API Uvicorn/FastAPI backend.

### 3. Endpoint Racine API Backend & Health Check
- **Fichiers** : [`/app/main.py`](/app/main.py)
- **Description** :
  - L'endpoint backend `GET /health` (et `GET /` avec header `Accept: application/json`) renvoie un message JSON structuré (`status: ok`, `service: Music Refs API`, `docs: /docs`), évitant les réponses 404 brutes.

### 4. Page d'Erreur 404 Personnalisée et Marquée
- **Fichiers** : [`404.html`](404.html), [`/app/main.py`](/app/main.py)
- **Description** :
  - Page d'erreur HTML 404 aux couleurs de Music Refs avec liens de navigation vers l'accueil (`/`) et la documentation API (`/docs`).
  - Gestionnaire d'exception 404 backend adaptatif (HTML pour navigateur, JSON structuré pour les requêtes API).

---

## 🧪 Suite de Tests Automated

- **Tests unitaires et d'intégration Backend & Routage (Python unittest)** : [`tests/test_music_refs.py`](tests/test_music_refs.py)
  - 11 tests automatisés couvrant les User Stories des tâches #4 et #5 (`python3 -m unittest discover -s /workspace/music-refs/tests`).

---

## 📌 Informations Git & Branche

- **Branche de feature** : `ada-feature-5`
- **Remote Origin** : `origin`
- **Message de commit** : `feat: implement user stories for task #5`

