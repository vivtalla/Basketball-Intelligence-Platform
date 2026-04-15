from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, inspect, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.migrations import upgrade_database  # noqa: E402
def test_upgrade_database_creates_fresh_schema_from_migrations():
    with TemporaryDirectory() as tmpdir:
        database_url = "sqlite:///{0}".format(Path(tmpdir) / "fresh.db")

        upgrade_database(database_url)

        engine = create_engine(database_url)
        try:
            inspector = inspect(engine)
            tables = set(inspector.get_table_names())
            assert "players" in tables
            assert "season_stats" in tables
            assert "team_season_stats" in tables
            assert "team_split_stats" in tables
            assert "team_standings" in tables
            assert "shot_lab_snapshots" in tables
            assert "alembic_version" in tables
        finally:
            engine.dispose()


def test_upgrade_database_stamps_legacy_sqlite_schema_and_applies_drift_columns():
    with TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "legacy.db"
        conn = sqlite3.connect(db_path)
        try:
            conn.executescript(
                """
                CREATE TABLE season_stats (
                    id INTEGER PRIMARY KEY,
                    player_id INTEGER NOT NULL,
                    season VARCHAR(20) NOT NULL,
                    team_abbreviation VARCHAR(10) NOT NULL,
                    is_playoff BOOLEAN NOT NULL DEFAULT 0
                );
                CREATE TABLE team_standings (
                    id INTEGER PRIMARY KEY,
                    team_id INTEGER NOT NULL,
                    season VARCHAR(20) NOT NULL,
                    updated_at DATETIME,
                    wins INTEGER,
                    losses INTEGER
                );
                INSERT INTO team_standings (team_id, season, updated_at, wins, losses)
                VALUES (1610612737, '2025-26', '2025-12-01 08:00:00', 10, 5);
                CREATE TABLE shot_lab_snapshots (
                    id INTEGER PRIMARY KEY,
                    snapshot_id VARCHAR(36)
                );
                """
            )
            conn.commit()
        finally:
            conn.close()

        database_url = "sqlite:///{0}".format(db_path)
        upgrade_database(database_url)

        engine = create_engine(database_url)
        try:
            inspector = inspect(engine)
            season_stat_columns = {column["name"] for column in inspector.get_columns("season_stats")}
            assert "darko" in season_stat_columns
            assert "clutch_pts" in season_stat_columns
            assert "fast_break_pts" in season_stat_columns

            team_standing_columns = {column["name"] for column in inspector.get_columns("team_standings")}
            assert "snapshot_date" in team_standing_columns

            shot_snapshot_columns = {column["name"] for column in inspector.get_columns("shot_lab_snapshots")}
            assert "route_path" in shot_snapshot_columns

            with engine.connect() as connection:
                alembic_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
                snapshot_date = connection.execute(text("SELECT snapshot_date FROM team_standings")).scalar_one()

            team_season_columns = {column["name"] for column in inspector.get_columns("team_season_stats")}
            assert "off_rating" in team_season_columns
            assert "tov_pct" in team_season_columns

            team_split_columns = {column["name"] for column in inspector.get_columns("team_split_stats")}
            assert "split_family" in team_split_columns
            assert "plus_minus" in team_split_columns

            assert alembic_revision == "0004_team_split_stats"
            assert snapshot_date == "2025-12-01"
        finally:
            engine.dispose()
