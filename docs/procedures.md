# Procédures Music Refs (sans secrets)

Pour le token admin en clair (environnement QA), voir le fichier local non versionné  
`ACCES-ET-PROCEDURES.md` à la racine du projet, ou la variable `ADMIN_TOKEN` dans `.env`.

## URLs

| Usage | URL |
|---|---|
| Jeu | https://music-refs-dev.kladriva.ca/ |
| Admin (catalogue + import) | https://music-refs-dev.kladriva.ca/admin.html |
| Swagger | https://music-refs-dev.kladriva.ca/docs |
| Health | https://music-refs-dev.kladriva.ca/health |
| Port local | `http://127.0.0.1:8084` |

## Démarrer

```bash
cd /home/steflight/qa-environment/music-refs
cp -n .env.example .env   # puis éditer ADMIN_TOKEN
docker compose up -d --build
curl -sS http://127.0.0.1:8084/health
```

## Peupler (UI)

1. Ouvrir `/admin.html`, coller le token.  
2. Consulter le **catalogue** (punchline + artiste/titre).  
3. **Import** : artiste + titre → cocher les lignes → enregistrer.

## Peupler (CLI)

```bash
TOKEN="$(grep '^ADMIN_TOKEN=' .env | cut -d= -f2)"

curl -sS -X POST http://127.0.0.1:8084/api/music-refs/import \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: $TOKEN" \
  -d '{"artist":"Damso","title":"Macarena"}'
```

## Conception

- Plan : [conception/01-api-lyrics-sans-ia.md](conception/01-api-lyrics-sans-ia.md)  
- Checklist : [conception/statut-implementation.md](conception/statut-implementation.md)  
