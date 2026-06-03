# Tableau de bord DPI

Projet initialise avec:

- Frontend: Vue.js 3 + Vite
- Backend: FastAPI + SQLAlchemy
- Source de donnees: table SQL configurable par variables d'environnement

## Structure

```text
Tableau_bord/
  backend/
    app/
      main.py
      config.py
      database.py
      table_reader.py
    requirements.txt
    .env.example
    .env.production.example
    Dockerfile
  frontend/
    src/
      App.vue
      main.js
      services/api.js
      assets/main.css
    package.json
    vite.config.js
    .env.example
    .env.production.example
    Dockerfile
  docker-compose.yml
  DEPLOYMENT.md
```

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/create_sample_db.py
uvicorn app.main:app --reload --port 8000
```

Modifie ensuite `backend/.env`:

```env
DATABASE_URL=sqlite:///./data/dashboard.db
SQL_TABLE_NAME=suivi_dpi_sites
SQL_SCHEMA=
```

Exemples de `DATABASE_URL`:

- SQLite: `sqlite:///./data/dashboard.db`
- PostgreSQL: `postgresql+psycopg://user:password@localhost:5432/database`
- MySQL: `mysql+pymysql://user:password@localhost:3306/database`
- SQL Server: `mssql+pyodbc:///?odbc_connect=...`

Installe le driver Python adapte si tu utilises PostgreSQL, MySQL ou SQL Server.

Le script `python scripts/create_sample_db.py` cree une table SQLite locale
`suivi_dpi_sites` compatible avec les indicateurs du tableau de bord avant le
branchement a la vraie base.

## Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Le frontend attend l'API sur `http://localhost:8000` par defaut. Tu peux changer cette URL dans `frontend/.env`.

## Deploiement

Les fichiers Docker, `.dockerignore`, `docker-compose.yml` et les exemples
`.env.production.example` sont fournis. Consulte `DEPLOYMENT.md` pour les
variables a definir sur l'hebergeur et le test local avec Docker.

## API principale

- `GET /api/health`
- `GET /api/table`
- `GET /api/overview`
- `GET /api/rows?limit=25&offset=0`
- `GET /api/group-by/{column}`
