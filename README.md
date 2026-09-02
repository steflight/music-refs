# Music Refs - Le Jeu des Punchlines & Citations (Task #6)

**Music Refs** est une application web moderne et interactive permettant aux passionnés de musique de deviner des artistes et des chansons à partir de citations et punchlines tirées au sort.

---

## 🎯 User Stories Implémentées (Task #6 - SSL/TLS, Reverse Proxy SNI & Surveillance)

### 1. Provisionnement et Configuration de Certificat SSL/TLS pour le Sous-Domaine
- **Fichiers** : [`certs/music-refs-dev.kladriva.ca.crt`](certs/music-refs-dev.kladriva.ca.crt), [`certs/music-refs-dev.kladriva.ca.key`](certs/music-refs-dev.kladriva.ca.key), [`scripts/cert_manager.py`](scripts/cert_manager.py)
- **Description** :
  - Génération et provisionnement de certificats SSL/TLS RSA 2048-bit avec extension SAN (Subject Alternative Name) pour `music-refs-dev.kladriva.ca`.
  - Résout le problème `ERR_SSL_UNRECOGNIZED_NAME_ALERT` en garantissant un handshake TLS valide.

### 2. Configuration Reverse Proxy SNI & Hôtes Virtuels
- **Fichiers** : [`nginx.conf`](nginx.conf)
- **Description** :
  - Mis à jour pour supporter la gestion SNI sur le port 443 avec HTTP/2.
  - Redirection automatique HTTP (80) vers HTTPS (443).
  - Protocoles sécurisés activés : `TLSv1.2` et `TLSv1.3`.
  - En-têtes de sécurité HSTS (`Strict-Transport-Security`), `X-Frame-Options`, `X-Content-Type-Options`.

### 3. Gestion Automatisée et Renouvellement des Certificats SSL
- **Fichiers** : [`scripts/cert_manager.py`](scripts/cert_manager.py)
- **Description** :
  - Script automatisé pour vérifier l'expiration du certificat et déclencher le renouvellement automatique lorsque l'échéance est inférieure au seuil (ex: 30 jours) ou sur demande force (`--force`).

### 4. Surveillance des Handshakes SSL/TLS et de la Santé du Domaine
- **Fichiers** : [`scripts/ssl_monitor.py`](scripts/ssl_monitor.py)
- **Description** :
  - Script de surveillance qui effectue un test de handshake TLS réel avec SNI, vérifie la chaîne de certificats, contrôle la disponibilité de l'endpoint d'API (`/health`) et génère un rapport de santé JSON structuré (`OK`, `WARNING`, `CRITICAL`).

---

## 🧪 Suite de Tests Automated

- **Tests unitaires et d'intégration (Python unittest)** : [`tests/test_music_refs.py`](tests/test_music_refs.py)
  - 15 tests automatisés couvrant l'ensemble des fonctionnalités des tâches #4, #5 et #6 (`python3 -m unittest discover -s /workspace/music-refs/tests`).

---

## 📌 Informations Git & Branche

- **Branche de feature** : `ada-feature-6`
- **Remote Origin** : `origin`
- **Message de commit** : `feat: implement user stories for task #6`
