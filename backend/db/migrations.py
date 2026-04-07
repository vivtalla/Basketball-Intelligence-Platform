from __future__ import annotations

from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from config import DATABASE_URL


BASELINE_REVISION = "0001_base_schema"


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _alembic_config(database_url: Optional[str] = None) -> Config:
    root = _backend_root()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url or DATABASE_URL)
    return config


def _has_existing_app_schema(database_url: str) -> bool:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        return bool(tables - {"alembic_version"})
    finally:
        engine.dispose()


def _has_alembic_version_table(database_url: str) -> bool:
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        inspector = inspect(engine)
        return "alembic_version" in inspector.get_table_names()
    finally:
        engine.dispose()


def upgrade_database(database_url: Optional[str] = None, revision: str = "head") -> None:
    target_url = database_url or DATABASE_URL
    config = _alembic_config(target_url)

    if not _has_alembic_version_table(target_url) and _has_existing_app_schema(target_url):
        command.stamp(config, BASELINE_REVISION)

    command.upgrade(config, revision)


def stamp_database(database_url: Optional[str] = None, revision: str = BASELINE_REVISION) -> None:
    config = _alembic_config(database_url)
    command.stamp(config, revision)


if __name__ == "__main__":
    upgrade_database()
