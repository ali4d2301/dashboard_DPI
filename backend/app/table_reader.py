from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from time import monotonic
from typing import Any
import unicodedata

from sqlalchemy import MetaData, Table, case, func, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.sql.sqltypes import Float, Integer, Numeric

from .config import settings
from .database import engine

CACHE_TTL_SECONDS = 300
_rows_cache: dict[str, Any] = {"expires_at": 0.0, "rows": []}


def _load_table(db: Engine = engine) -> Table:
    metadata = MetaData()
    try:
        return Table(
            settings.sql_table_name,
            metadata,
            autoload_with=db,
            schema=settings.sql_schema,
        )
    except NoSuchTableError as exc:
        qualified_name = (
            f"{settings.sql_schema}.{settings.sql_table_name}"
            if settings.sql_schema
            else settings.sql_table_name
        )
        raise RuntimeError(f"SQL table not found: {qualified_name}") from exc


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row.items()}


def _region_filter(table: Table, region: str | None):
    if not region:
        return None
    if "region_sanitaire" not in table.columns:
        raise ValueError("Unknown column: region_sanitaire")
    return table.columns.region_sanitaire == region.strip()


def _apply_region_filter(statement, table: Table, region: str | None):
    condition = _region_filter(table, region)
    return statement.where(condition) if condition is not None else statement


def _table_columns(table: Table) -> list[dict[str, Any]]:
    return [
        {
            "name": column.name,
            "type": str(column.type),
            "nullable": bool(column.nullable),
            "primary_key": bool(column.primary_key),
        }
        for column in table.columns
    ]


def _fetch_all_rows_cached(table: Table) -> list[dict[str, Any]]:
    now = monotonic()
    if _rows_cache["expires_at"] > now:
        return _rows_cache["rows"]

    with engine.connect() as connection:
        rows = connection.execute(select(table)).mappings()
        data = [_serialize_row(dict(row)) for row in rows]

    _rows_cache["rows"] = data
    _rows_cache["expires_at"] = now + CACHE_TTL_SECONDS
    return data


def _normalize_group_label(value: str) -> str:
    normalized = unicodedata.normalize("NFD", str(value or ""))
    without_accents = "".join(
        char for char in normalized if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_accents.lower().split())


def _clean_label(value: Any, fallback: str = "Non renseign\u00e9") -> str:
    if value is None or str(value).strip() == "":
        return fallback
    return str(_json_value(value))


def _is_deployed(value: Any) -> bool:
    return "ploy" in _normalize_group_label(str(value or ""))


def _is_functional(value: Any) -> bool:
    return _normalize_group_label(str(value or "")) == "fonctionnel"


def _is_partial(value: Any) -> bool:
    return "partiellement" in _normalize_group_label(str(value or ""))


def _is_non_functional(value: Any) -> bool:
    return _normalize_group_label(str(value or "")).startswith("non fonctionnel")


def _is_not_deployed(value: Any) -> bool:
    normalized = _normalize_group_label(str(value or ""))
    return normalized in {"non demarre", "en cours"}


def _group_items(rows: list[dict[str, Any]], column_name: str, limit: int) -> list[dict[str, Any]]:
    counter = Counter(
        label
        for label in (_clean_label(row.get(column_name)) for row in rows)
        if _normalize_group_label(label) != "non renseigne"
    )
    return [
        {"label": label, "count": count}
        for label, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _performance_items_from_rows(
    rows: list[dict[str, Any]],
    column_name: str,
    limit: int,
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, int | str]] = {}

    for row in rows:
        label = _clean_label(row.get(column_name))
        current = groups.setdefault(
            label,
            {
                "label": label,
                "supported": 0,
                "deployed": 0,
                "functional": 0,
                "partial": 0,
                "nonFunctional": 0,
            },
        )
        current["supported"] = int(current["supported"]) + 1
        if _is_deployed(row.get("statut_deploiement")):
            current["deployed"] = int(current["deployed"]) + 1
        if _is_functional(row.get("statut_operationnel")):
            current["functional"] = int(current["functional"]) + 1
        if _is_partial(row.get("statut_operationnel")):
            current["partial"] = int(current["partial"]) + 1
        if _is_non_functional(row.get("statut_operationnel")):
            current["nonFunctional"] = int(current["nonFunctional"]) + 1

    items = []
    for item in sorted(groups.values(), key=lambda value: int(value["supported"]), reverse=True)[:limit]:
        supported = int(item["supported"])
        deployed = int(item["deployed"])
        functional = int(item["functional"])
        unavailable = int(item["partial"]) + int(item["nonFunctional"])
        items.append(
            {
                "label": item["label"],
                "supported": supported,
                "deployed": deployed,
                "deploymentRate": (deployed / supported * 100) if supported else 0,
                "functional": functional,
                "functionalityRate": (functional / deployed * 100) if deployed else 0,
                "nonFunctional": unavailable,
            }
        )

    return items


def _district_detail_items_from_rows(
    rows: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], dict[str, Any]] = {}

    for row in rows:
        region = _clean_label(row.get("region_sanitaire"))
        district = _clean_label(row.get("district_sanitaire"))
        current = groups.setdefault(
            (region, district),
            {
                "region": region,
                "district": district,
                "supported": 0,
                "deployed": 0,
                "functional": 0,
                "partial": 0,
                "nonFunctional": 0,
            },
        )
        current["supported"] += 1
        if _is_deployed(row.get("statut_deploiement")):
            current["deployed"] += 1
        if _is_functional(row.get("statut_operationnel")):
            current["functional"] += 1
        if _is_partial(row.get("statut_operationnel")):
            current["partial"] += 1
        if _is_non_functional(row.get("statut_operationnel")):
            current["nonFunctional"] += 1

    items = []
    for item in sorted(groups.values(), key=lambda value: (value["region"], value["district"]))[:limit]:
        supported = int(item["supported"])
        deployed = int(item["deployed"])
        functional = int(item["functional"])
        partial = int(item["partial"])
        non_functional = int(item["nonFunctional"])
        gap = max(supported - deployed, 0)
        items.append(
            {
                "region": item["region"],
                "district": item["district"],
                "supported": supported,
                "deployed": deployed,
                "deploymentRate": (deployed / supported * 100) if supported else 0,
                "functional": functional,
                "functionalRate": (functional / deployed * 100) if deployed else 0,
                "partial": partial,
                "partialRate": (partial / deployed * 100) if deployed else 0,
                "nonFunctional": non_functional,
                "nonFunctionalRate": (non_functional / deployed * 100) if deployed else 0,
                "gap": gap,
                "gapRate": (gap / supported * 100) if supported else 0,
            }
        )

    return items


def _status_sort_key(status: str) -> tuple[int, str]:
    preferred = ["deploye", "en cours", "non demarre", "non renseigne"]
    normalized = _normalize_group_label(status)
    return (
        preferred.index(normalized) if normalized in preferred else len(preferred),
        status,
    )


def _deployment_reference_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    reference_types = {
        "institut specialisees",
        "chu public",
        "chr public",
        "hg public",
    }
    reference_label = "Ets R\u00e9f\u00e9rence"
    groups = {
        reference_label: {"label": reference_label, "total": 0, "statuses": {}},
        "ESPC": {"label": "ESPC", "total": 0, "statuses": {}},
    }

    for row in rows:
        type_label = _clean_label(row.get("type_etablissement"), "")
        status_label = _clean_label(row.get("statut_deploiement"))
        group_label = (
            reference_label
            if _normalize_group_label(type_label) in reference_types
            else "ESPC"
        )
        groups[group_label]["total"] += 1
        groups[group_label]["statuses"][status_label] = (
            groups[group_label]["statuses"].get(status_label, 0) + 1
        )

    status_labels = sorted(
        {status for group in groups.values() for status in group["statuses"]},
        key=_status_sort_key,
    )

    return {
        "items": [
            {
                "label": group["label"],
                "total": group["total"],
                "statuses": [
                    {
                        "label": status,
                        "count": group["statuses"].get(status, 0),
                        "rate": (
                            group["statuses"].get(status, 0) / group["total"] * 100
                            if group["total"]
                            else 0
                        ),
                    }
                    for status in status_labels
                ],
            }
            for group in groups.values()
        ],
        "statuses": status_labels,
    }


def _operational_bailleur_from_rows(
    rows: list[dict[str, Any]],
    limit: int,
) -> dict[str, Any]:
    status_order = [
        ("Utilisés", "functional"),
        ("Partiellement utilisés", "partial"),
        ("Non utilisés", "non_functional"),
        ("Non d\u00e9ploy\u00e9", "not_deployed"),
    ]
    groups: dict[str, dict[str, Any]] = {}

    for row in rows:
        label = _clean_label(row.get("bailleur"))
        current = groups.setdefault(
            label,
            {
                "label": label,
                "total": 0,
                "functional": 0,
                "partial": 0,
                "non_functional": 0,
                "not_deployed": 0,
            },
        )
        current["total"] += 1

        if _is_not_deployed(row.get("statut_deploiement")):
            current["not_deployed"] += 1
        elif _is_functional(row.get("statut_operationnel")):
            current["functional"] += 1
        elif _is_partial(row.get("statut_operationnel")):
            current["partial"] += 1
        else:
            current["non_functional"] += 1

    items = []
    for group in sorted(groups.values(), key=lambda value: value["total"], reverse=True)[:limit]:
        total = int(group["total"])
        items.append(
            {
                "label": group["label"],
                "total": total,
                "statuses": [
                    {
                        "label": label,
                        "count": int(group[field]),
                        "rate": (int(group[field]) / total * 100) if total else 0,
                    }
                    for label, field in status_order
                ],
            }
        )

    return {"items": items, "statuses": [label for label, _ in status_order]}


def _region_summary_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    supported = len(rows)
    deployed = sum(1 for row in rows if _is_deployed(row.get("statut_deploiement")))
    functional = sum(1 for row in rows if _is_functional(row.get("statut_operationnel")))

    return {
        "supported": supported,
        "deployed": deployed,
        "functional": functional,
        "deploymentRate": (deployed / supported * 100) if supported else 0,
        "functionalityRate": (functional / deployed * 100) if deployed else 0,
    }


def _numeric_summary_from_rows(
    table: Table,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    numeric_columns = [
        column
        for column in table.columns
        if isinstance(column.type, (Integer, Float, Numeric))
    ]
    summaries = []

    for column in numeric_columns[:8]:
        values = [
            float(value)
            for value in (row.get(column.name) for row in rows)
            if isinstance(value, (int, float, Decimal))
        ]
        if not values:
            continue
        summaries.append(
            {
                "name": column.name,
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
            }
        )

    return summaries


def dashboard_snapshot(region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    all_rows = _fetch_all_rows_cached(table)
    selected_region = region.strip() if region else ""
    rows_by_region: dict[str, list[dict[str, Any]]] = {}
    for row in all_rows:
        region_label = _clean_label(row.get("region_sanitaire"))
        rows_by_region.setdefault(region_label, []).append(row)

    filtered_rows = [
        row
        for row in all_rows
        if not selected_region or str(row.get("region_sanitaire") or "") == selected_region
    ]
    district_items = _district_detail_items_from_rows(filtered_rows, 200)

    return {
        "overview": {
            "table": settings.sql_table_name,
            "schema": settings.sql_schema,
            "total_rows": len(filtered_rows),
            "columns": _table_columns(table),
            "numeric_summary": _numeric_summary_from_rows(table, filtered_rows),
        },
        "rowsPayload": {
            "table": settings.sql_table_name,
            "limit": 80,
            "offset": 0,
            "rows": filtered_rows[:80],
        },
        "groupings": {
            "regions": _group_items(all_rows, "region_sanitaire", 50),
            "bailleurs": _group_items(filtered_rows, "bailleur", 50),
            "deployment": _group_items(filtered_rows, "statut_deploiement", 20),
            "operational": _group_items(filtered_rows, "statut_operationnel", 20),
            "motifs": _group_items(filtered_rows, "motif_principal", 20),
            "types": _group_items(filtered_rows, "type_etablissement", 14),
        },
        "typePerformancePayload": {
            "column": "type_etablissement",
            "items": _performance_items_from_rows(filtered_rows, "type_etablissement", 14),
        },
        "deploymentReferencePayload": _deployment_reference_from_rows(filtered_rows),
        "districtDetailsPayload": {"items": district_items, "total": len(district_items)},
        "operationalBailleurPayload": _operational_bailleur_from_rows(filtered_rows, 6),
        "regionSummaryPayload": {
            region_label: _region_summary_from_rows(region_rows)
            for region_label, region_rows in rows_by_region.items()
        },
    }


def list_columns() -> list[dict[str, Any]]:
    inspector = inspect(engine)
    columns = inspector.get_columns(settings.sql_table_name, schema=settings.sql_schema)
    return [
        {
            "name": column["name"],
            "type": str(column["type"]),
            "nullable": bool(column.get("nullable", True)),
            "primary_key": bool(column.get("primary_key", False)),
        }
        for column in columns
    ]


def list_tables() -> list[dict[str, Any]]:
    inspector = inspect(engine)
    table_names = inspector.get_table_names(schema=settings.sql_schema)

    summaries = []
    with engine.connect() as connection:
        for table_name in table_names:
            table = Table(
                table_name,
                MetaData(),
                autoload_with=engine,
                schema=settings.sql_schema,
            )
            total_rows = connection.execute(select(func.count()).select_from(table)).scalar_one()
            summaries.append({"name": table_name, "total_rows": total_rows})

    return summaries


def fetch_rows(limit: int = 25, offset: int = 0, region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    safe_limit = max(1, min(limit, 5000))
    safe_offset = max(0, offset)
    selected_region = region.strip() if region else ""
    all_rows = _fetch_all_rows_cached(table)
    filtered_rows = [
        row
        for row in all_rows
        if not selected_region or str(row.get("region_sanitaire") or "") == selected_region
    ]
    data = filtered_rows[safe_offset : safe_offset + safe_limit]

    return {
        "table": settings.sql_table_name,
        "limit": safe_limit,
        "offset": safe_offset,
        "total_rows": len(filtered_rows),
        "rows": data,
    }


def get_table_overview(region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    numeric_columns = [
        column
        for column in table.columns
        if isinstance(column.type, (Integer, Float, Numeric))
    ]

    with engine.connect() as connection:
        total_rows = connection.execute(
            _apply_region_filter(select(func.count()).select_from(table), table, region)
        ).scalar_one()
        numeric_summary = []

        for column in numeric_columns[:8]:
            summary = connection.execute(
                _apply_region_filter(
                    select(
                        func.min(column),
                        func.max(column),
                        func.avg(column),
                    ).select_from(table),
                    table,
                    region,
                )
            ).one()
            numeric_summary.append(
                {
                    "name": column.name,
                    "min": _json_value(summary[0]),
                    "max": _json_value(summary[1]),
                    "avg": _json_value(summary[2]),
                }
            )

    return {
        "table": settings.sql_table_name,
        "schema": settings.sql_schema,
        "total_rows": total_rows,
        "columns": list_columns(),
        "numeric_summary": numeric_summary,
    }


def group_by_column(column_name: str, limit: int = 12, region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    if column_name not in table.columns:
        raise ValueError(f"Unknown column: {column_name}")

    column = table.columns[column_name]
    safe_limit = max(1, min(limit, 50))
    statement = _apply_region_filter(
        select(column, func.count().label("count"))
        .group_by(column)
        .order_by(func.count().desc())
        .limit(safe_limit),
        table,
        region,
    )

    with engine.connect() as connection:
        rows = connection.execute(statement).all()

    return {
        "column": column_name,
        "items": [
            {"label": str(_json_value(row[0])), "count": int(row[1])}
            for row in rows
        ],
    }


def performance_by_column(column_name: str, limit: int = 12, region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    required_columns = [
        column_name,
        "statut_deploiement",
        "statut_operationnel",
    ]
    missing_columns = [name for name in required_columns if name not in table.columns]
    if missing_columns:
        raise ValueError(f"Unknown column(s): {', '.join(missing_columns)}")

    group_column = table.columns[column_name]
    deployment_column = table.columns.statut_deploiement
    operational_column = table.columns.statut_operationnel
    safe_limit = max(1, min(limit, 50))

    deployed_count = func.sum(
        case((deployment_column.like("%ploy%"), 1), else_=0)
    ).label("deployed")
    functional_count = func.sum(
        case((operational_column == "Fonctionnel", 1), else_=0)
    ).label("functional")
    partial_count = func.sum(
        case((operational_column == "Partiellement fonctionnel", 1), else_=0)
    ).label("partial")
    non_functional_count = func.sum(
        case((operational_column == "Non fonctionnel", 1), else_=0)
    ).label("non_functional")
    supported_count = func.count().label("supported")
    statement = _apply_region_filter(
        select(
            group_column.label("label"),
            supported_count,
            deployed_count,
            functional_count,
            partial_count,
            non_functional_count,
        )
        .group_by(group_column)
        .order_by(supported_count.desc())
        .limit(safe_limit),
        table,
        region,
    )

    with engine.connect() as connection:
        rows = connection.execute(statement).all()

    items = []
    for row in rows:
        supported = int(row.supported or 0)
        deployed = int(row.deployed or 0)
        functional = int(row.functional or 0)
        unavailable = int(row.partial or 0) + int(row.non_functional or 0)
        items.append(
            {
                "label": str(_json_value(row.label) or "Non renseigne"),
                "supported": supported,
                "deployed": deployed,
                "deploymentRate": (deployed / supported * 100) if supported else 0,
                "functional": functional,
                "functionalityRate": (functional / deployed * 100) if deployed else 0,
                "nonFunctional": unavailable,
            }
        )

    return {"column": column_name, "items": items}


def district_detail_rows(limit: int = 200, region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    required_columns = [
        "region_sanitaire",
        "district_sanitaire",
        "statut_deploiement",
        "statut_operationnel",
    ]
    missing_columns = [name for name in required_columns if name not in table.columns]
    if missing_columns:
        raise ValueError(f"Unknown column(s): {', '.join(missing_columns)}")

    region_column = table.columns.region_sanitaire
    district_column = table.columns.district_sanitaire
    deployment_column = table.columns.statut_deploiement
    operational_column = table.columns.statut_operationnel
    safe_limit = max(1, min(limit, 250))

    supported_count = func.count().label("supported")
    deployed_count = func.sum(
        case((deployment_column.like("%ploy%"), 1), else_=0)
    ).label("deployed")
    functional_count = func.sum(
        case((operational_column == "Fonctionnel", 1), else_=0)
    ).label("functional")
    partial_count = func.sum(
        case((operational_column == "Partiellement fonctionnel", 1), else_=0)
    ).label("partial")
    non_functional_count = func.sum(
        case((operational_column == "Non fonctionnel", 1), else_=0)
    ).label("non_functional")
    statement = _apply_region_filter(
        select(
            region_column.label("region"),
            district_column.label("district"),
            supported_count,
            deployed_count,
            functional_count,
            partial_count,
            non_functional_count,
        )
        .group_by(region_column, district_column)
        .order_by(region_column, district_column)
        .limit(safe_limit),
        table,
        region,
    )

    with engine.connect() as connection:
        rows = connection.execute(statement).all()

    items = []
    for row in rows:
        supported = int(row.supported or 0)
        deployed = int(row.deployed or 0)
        functional = int(row.functional or 0)
        partial = int(row.partial or 0)
        non_functional = int(row.non_functional or 0)
        gap = max(supported - deployed, 0)

        items.append(
            {
                "region": str(_json_value(row.region) or "Non renseigne"),
                "district": str(_json_value(row.district) or "Non renseigne"),
                "supported": supported,
                "deployed": deployed,
                "deploymentRate": (deployed / supported * 100) if supported else 0,
                "functional": functional,
                "functionalRate": (functional / deployed * 100) if deployed else 0,
                "partial": partial,
                "partialRate": (partial / deployed * 100) if deployed else 0,
                "nonFunctional": non_functional,
                "nonFunctionalRate": (non_functional / deployed * 100) if deployed else 0,
                "gap": gap,
                "gapRate": (gap / supported * 100) if supported else 0,
            }
        )

    return {"items": items, "total": len(items)}


def deployment_status_by_reference_groups(region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    required_columns = ["type_etablissement", "statut_deploiement"]
    missing_columns = [name for name in required_columns if name not in table.columns]
    if missing_columns:
      raise ValueError(f"Unknown column(s): {', '.join(missing_columns)}")

    reference_types = {
        "institut specialisees",
        "chu public",
        "chr public",
        "hg public",
    }
    type_column = table.columns.type_etablissement
    status_column = table.columns.statut_deploiement

    groups = {
        "Ets Référence": {"label": "Ets Référence", "total": 0, "statuses": {}},
        "ESPC": {"label": "ESPC", "total": 0, "statuses": {}},
    }

    with engine.connect() as connection:
        rows = connection.execute(
            _apply_region_filter(
                select(
                    type_column.label("type_label"),
                    status_column.label("status_label"),
                    func.count().label("count"),
                )
                .group_by(type_column, status_column),
                table,
                region,
            )
        ).all()

    for row in rows:
        type_label = str(_json_value(row.type_label) or "")
        status_label = str(_json_value(row.status_label) or "Non renseigné")
        group_label = (
            "Ets Référence"
            if _normalize_group_label(type_label) in reference_types
            else "ESPC"
        )
        count = int(row.count or 0)
        groups[group_label]["total"] += count
        groups[group_label]["statuses"][status_label] = (
            groups[group_label]["statuses"].get(status_label, 0) + count
        )

    preferred_order = ["Déployé", "En cours", "Non démarré", "Non renseigné"]
    status_labels = sorted(
        {status for group in groups.values() for status in group["statuses"]},
        key=lambda status: (
            preferred_order.index(status) if status in preferred_order else len(preferred_order),
            status,
        ),
    )

    return {
        "items": [
            {
                "label": group["label"],
                "total": group["total"],
                "statuses": [
                    {
                        "label": status,
                        "count": group["statuses"].get(status, 0),
                        "rate": (
                            group["statuses"].get(status, 0) / group["total"] * 100
                            if group["total"]
                            else 0
                        ),
                    }
                    for status in status_labels
                ],
            }
            for group in groups.values()
        ],
        "statuses": status_labels,
    }


def operational_status_by_bailleur(limit: int = 6, region: str | None = None) -> dict[str, Any]:
    table = _load_table()
    required_columns = [
        "bailleur",
        "statut_deploiement",
        "statut_operationnel",
    ]
    missing_columns = [name for name in required_columns if name not in table.columns]
    if missing_columns:
        raise ValueError(f"Unknown column(s): {', '.join(missing_columns)}")

    bailleur_column = table.columns.bailleur
    deployment_column = table.columns.statut_deploiement
    operational_column = table.columns.statut_operationnel
    safe_limit = max(1, min(limit, 20))

    functional_count = func.sum(
        case((operational_column == "Fonctionnel", 1), else_=0)
    ).label("functional")
    partial_count = func.sum(
        case((operational_column == "Partiellement fonctionnel", 1), else_=0)
    ).label("partial")
    non_functional_count = func.sum(
        case((operational_column == "Non fonctionnel", 1), else_=0)
    ).label("non_functional")
    not_deployed_count = func.sum(
        case((deployment_column.in_(["Non démarré", "En cours"]), 1), else_=0)
    ).label("not_deployed")
    total_count = func.count().label("total")
    statement = _apply_region_filter(
        select(
            bailleur_column.label("label"),
            total_count,
            functional_count,
            partial_count,
            non_functional_count,
            not_deployed_count,
        )
        .group_by(bailleur_column)
        .order_by(total_count.desc())
        .limit(safe_limit),
        table,
        region,
    )

    with engine.connect() as connection:
        rows = connection.execute(statement).all()

    status_order = [
        ("Utilisés", "functional"),
        ("Partiellement utilisés", "partial"),
        ("Non utilisés", "non_functional"),
        ("Non déployé", "not_deployed"),
    ]

    items = []
    for row in rows:
        total = int(row.total or 0)
        items.append(
            {
                "label": str(_json_value(row.label) or "Non renseigné"),
                "total": total,
                "statuses": [
                    {
                        "label": label,
                        "count": int(getattr(row, field) or 0),
                        "rate": (
                            int(getattr(row, field) or 0) / total * 100
                            if total
                            else 0
                        ),
                    }
                    for label, field in status_order
                ],
            }
        )

    return {"items": items, "statuses": [label for label, _ in status_order]}
