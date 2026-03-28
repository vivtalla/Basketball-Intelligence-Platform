"""Schema utilities for evolving the app without Alembic.

Run `python -m db.ensure_schema` from backend/ directory to apply missing columns.
"""

from sqlalchemy import inspect, text
from db.database import engine
from db.models import Base


def ensure_column_exists(engine, table_name, column_name, column_type):
    insp = inspect(engine)
    if table_name not in insp.get_table_names():
        return  # table created by Base.metadata.create_all; skip
    columns = [c["name"] for c in insp.get_columns(table_name)]
    if column_name not in columns:
        print(f"Adding column {column_name} to {table_name}...")
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            conn.commit()
    else:
        print(f"Column {column_name} already exists in {table_name}.")


def ensure_new_tables(engine):
    """Create any new tables defined in models but not yet in the DB."""
    Base.metadata.create_all(bind=engine)


def apply_schema_updates():
    # Create new tables (game_logs, play_by_play, player_on_off, lineup_stats)
    ensure_new_tables(engine)

    # Existing columns
    ensure_column_exists(engine, "season_stats", "darko", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "epm", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "rapm", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "lebron", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "raptor", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "pipm", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "obpm", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "dbpm", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "ftr", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "par3", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "ast_tov", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "oreb_pct", "DOUBLE PRECISION")
    # Play-by-play derived columns
    ensure_column_exists(engine, "season_stats", "clutch_pts", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "clutch_fg_pct", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "clutch_plus_minus", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "second_chance_pts", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "fast_break_pts", "DOUBLE PRECISION")


if __name__ == "__main__":
    apply_schema_updates()
