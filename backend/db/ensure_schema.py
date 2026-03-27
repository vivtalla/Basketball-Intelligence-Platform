"""Schema utilities for evolving the app without Alembic.

Run `python -m db.ensure_schema` from backend/ directory to apply missing columns.
"""

from sqlalchemy import inspect
from sqlalchemy import text
from db.database import engine
from db.models import SeasonStat


def ensure_column_exists(engine, table_name, column_name, column_type):
    insp = inspect(engine)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    if column_name not in columns:
        print(f"Adding column {column_name} to {table_name}...")
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            conn.commit()
    else:
        print(f"Column {column_name} already exists in {table_name}.")


def apply_schema_updates():
    ensure_column_exists(engine, "season_stats", "darko", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "epm", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "rapm", "DOUBLE PRECISION")


if __name__ == "__main__":
    apply_schema_updates()
