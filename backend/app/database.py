from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import settings


def build_engine() -> Engine:
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = build_engine()
