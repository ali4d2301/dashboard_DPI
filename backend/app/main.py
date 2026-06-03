from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .table_reader import (
    dashboard_snapshot,
    deployment_status_by_reference_groups,
    district_detail_rows,
    fetch_rows,
    get_table_overview,
    group_by_column,
    list_tables,
    operational_status_by_bailleur,
    performance_by_column,
)


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _database_error(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail=(
            "Impossible de lire la table SQL. Verifie DATABASE_URL, "
            f"SQL_TABLE_NAME et SQL_SCHEMA. Detail: {exc}"
        ),
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/api/table")
def table_metadata() -> dict[str, str | None]:
    return {
        "table": settings.sql_table_name,
        "schema": settings.sql_schema,
        "database_url": settings.database_url.split("@")[-1],
    }


@app.get("/api/tables")
def tables() -> dict:
    try:
        return {"tables": list_tables()}
    except SQLAlchemyError as exc:
        raise _database_error(exc) from exc


@app.get("/api/overview")
def overview(region: str | None = Query(default=None)) -> dict:
    try:
        return get_table_overview(region=region)
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc


@app.get("/api/dashboard-snapshot")
def dashboard_snapshot_route(region: str | None = Query(default=None)) -> dict:
    try:
        return dashboard_snapshot(region=region)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc


@app.get("/api/rows")
def rows(
    limit: int = Query(default=25, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    region: str | None = Query(default=None),
) -> dict:
    try:
        return fetch_rows(limit=limit, offset=offset, region=region)
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc


@app.get("/api/group-by/{column_name}")
def grouped_values(
    column_name: str,
    limit: int = Query(default=12, ge=1, le=50),
    region: str | None = Query(default=None),
) -> dict:
    try:
        return group_by_column(column_name, limit=limit, region=region)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc


@app.get("/api/performance-by/{column_name}")
def performance_values(
    column_name: str,
    limit: int = Query(default=12, ge=1, le=50),
    region: str | None = Query(default=None),
) -> dict:
    try:
        return performance_by_column(column_name, limit=limit, region=region)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc


@app.get("/api/deployment-reference-groups")
def deployment_reference_groups(region: str | None = Query(default=None)) -> dict:
    try:
        return deployment_status_by_reference_groups(region=region)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc


@app.get("/api/district-details")
def district_details(
    limit: int = Query(default=200, ge=1, le=250),
    region: str | None = Query(default=None),
) -> dict:
    try:
        return district_detail_rows(limit=limit, region=region)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc


@app.get("/api/operational-by-bailleur")
def operational_by_bailleur(
    limit: int = Query(default=6, ge=1, le=20),
    region: str | None = Query(default=None),
) -> dict:
    try:
        return operational_status_by_bailleur(limit=limit, region=region)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, SQLAlchemyError) as exc:
        raise _database_error(exc) from exc
