from functools import lru_cache
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env", override=False)


class Settings:
    app_name: str
    app_env: str
    database_url: str
    sql_table_name: str
    sql_schema: str | None
    cors_origins: list[str]

    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "Tableau de bord DPI API")
        self.app_env = os.getenv("APP_ENV", "development")
        self.database_url = os.getenv("DATABASE_URL") or self._build_database_url()
        self.sql_table_name = os.getenv("SQL_TABLE_NAME", "suivi_dpi_sites")
        self.sql_schema = os.getenv("SQL_SCHEMA") or None
        origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        )
        self.cors_origins = [origin.strip() for origin in origins.split(",") if origin.strip()]

    def _build_database_url(self) -> str:
        host = os.getenv("DB_HOST")
        name = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        port = os.getenv("DB_PORT", "3306")

        if all([host, name, user, password]):
            return (
                f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
                f"@{host}:{port}/{quote_plus(name)}"
            )

        return "sqlite:///./data/dashboard.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
