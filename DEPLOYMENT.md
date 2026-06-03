# Deploiement

Ce projet est pret pour un deploiement en deux services:

- `backend`: API FastAPI exposee sur `/api/*`
- `frontend`: application Vue/Vite servie en statique

## Variables backend

Copier les valeurs de `backend/.env.production.example` dans les variables de l'hebergeur.

Variables obligatoires:

- `APP_ENV=production`
- `SQL_TABLE_NAME=suivi_dpi_sites`
- `CORS_ORIGINS=https://url-publique-du-frontend`
- soit `DATABASE_URL`, soit les variables `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

Ne pas publier `backend/.env`: il peut contenir les identifiants de la base.

## Variables frontend

Au build du frontend, definir:

```env
VITE_API_BASE_URL=https://url-publique-du-backend
```

Cette variable est injectee au moment du build Vite.

## Build local de verification

Backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall app scripts
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```

Frontend:

```powershell
cd frontend
npm.cmd ci
npm.cmd run build
```

## Test local avec Docker

```powershell
docker compose up --build
```

Ensuite ouvrir:

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000/api/health`

## Base exemple

Pour tester sans base externe:

```powershell
cd backend
Copy-Item .env.example .env
.\.venv\Scripts\python.exe scripts\create_sample_db.py
uvicorn app.main:app --reload --port 8000
```

Le script cree une table SQLite `suivi_dpi_sites` compatible avec les indicateurs du tableau de bord.
