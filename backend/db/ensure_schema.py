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
    # Create all ORM-declared tables, including Sprint 11 warehouse tables,
    # Sprint 13 request-throttle state, and legacy tables:
    # source_runs, ingestion_jobs, raw_schedule_payloads, games,
    # raw_game_payloads, game_team_stats, game_player_stats,
    # play_by_play_events, api_request_state, plus legacy tables.
    ensure_new_tables(engine)

    # Existing season_stats columns added incrementally over earlier sprints.
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
    ensure_column_exists(engine, "season_stats", "clutch_fga", "INTEGER")
    ensure_column_exists(engine, "season_stats", "clutch_fg_pct", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "clutch_plus_minus", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "second_chance_pts", "DOUBLE PRECISION")
    ensure_column_exists(engine, "season_stats", "fast_break_pts", "DOUBLE PRECISION")

    # No new columns were added to existing tables in Sprint 11 Phase 2.
    # Warehouse changes are additive new tables picked up by create_all().

    # Sprint 26 — Data Foundation: new tables picked up by create_all():
    #   player_injuries  (PlayerInjury)   — daily CDN injury report
    #   player_shot_charts (PlayerShotChart) — persisted shot chart JSONB
    #   team_standings   (TeamStanding)   — materialized standings per season
    # Sprint 27 — Injury identity hardening: new tables picked up by create_all():
    #   player_name_aliases     — durable player identity lookup variants
    #   injury_sync_unresolved  — unresolved official report rows for review
    # Sprint 38 — Platform overhaul: new tables picked up by create_all():
    #   shot_lab_snapshots      — shareable shot-lab state payloads
    # No new columns on existing tables this sprint.

    # Sprint 29 — Standings history: snapshot_date column + constraint migration
    ensure_column_exists(engine, "team_standings", "snapshot_date", "DATE")
    ensure_column_exists(engine, "shot_lab_snapshots", "route_path", "VARCHAR(255)")

    with engine.connect() as conn:
        # Backfill existing rows (idempotent — only updates NULLs)
        conn.execute(text(
            "UPDATE team_standings SET snapshot_date = updated_at::date WHERE snapshot_date IS NULL"
        ))
        # Enforce NOT NULL (idempotent)
        conn.execute(text("""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='team_standings'
                      AND column_name='snapshot_date'
                      AND is_nullable='YES'
                ) THEN
                    ALTER TABLE team_standings ALTER COLUMN snapshot_date SET NOT NULL;
                END IF;
            END $$;
        """))
        # Drop old unique constraint if it still exists
        conn.execute(text("""
            DO $$ BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_team_standing_season'
                      AND conrelid = 'team_standings'::regclass
                ) THEN
                    ALTER TABLE team_standings DROP CONSTRAINT uq_team_standing_season;
                END IF;
            END $$;
        """))
        # Add new unique constraint if it doesn't exist yet
        conn.execute(text("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_team_standing_season_date'
                      AND conrelid = 'team_standings'::regclass
                ) THEN
                    ALTER TABLE team_standings
                        ADD CONSTRAINT uq_team_standing_season_date
                        UNIQUE (team_id, season, snapshot_date);
                END IF;
            END $$;
        """))
        conn.commit()


if __name__ == "__main__":
    apply_schema_updates()
