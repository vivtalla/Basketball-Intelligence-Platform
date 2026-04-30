"""Sprint 79 Stream B — playoff PBP derivation indexes + NULL backfill.

No new columns: ``LineupStats.is_playoff`` and ``PlayerOnOff.is_playoff`` were both
introduced by ``0012_playoffs_data_layer``. This migration:

1. Backfills any rows that may have been written before ``0012`` ran (defensive).
2. Adds two indexes to make playoff-scoped queries fast:
   - ``ix_lineup_stats_playoff_team`` — primary access pattern for Series Intelligence
     (team_id + season + is_playoff lookups)
   - ``ix_player_on_off_playoff`` — enables fast playoff vs regular-season slicing

Idempotent: safe against fresh SQLite (no rows to backfill, indexes guarded).
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "0014_sprint79_playoff_indexes"
down_revision = "0013_sprint78_phase0_schemas"
branch_labels = None
depends_on = None


def _has_table(table_name):
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_index(table_name, index_name):
    inspector = inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _safe_create_index(index_name, table_name, columns, unique=False):
    if not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade():
    # Defensive backfill — any rows written before 0012 added is_playoff get coerced to FALSE.
    # Idempotent: WHERE clause filters to NULL only.
    # Use dialect-appropriate boolean literal: Postgres requires FALSE, SQLite accepts both.
    # Guard on table existence — some legacy stamped DBs may skip creating these.
    bind = op.get_bind()
    false_literal = "FALSE" if bind.dialect.name == "postgresql" else "0"

    if _has_table("lineup_stats"):
        op.execute(
            "UPDATE lineup_stats SET is_playoff = {0} WHERE is_playoff IS NULL".format(false_literal)
        )
        _safe_create_index(
            "ix_lineup_stats_playoff_team",
            "lineup_stats",
            ["season", "team_id", "is_playoff"],
        )

    if _has_table("player_on_off"):
        op.execute(
            "UPDATE player_on_off SET is_playoff = {0} WHERE is_playoff IS NULL".format(false_literal)
        )
        _safe_create_index(
            "ix_player_on_off_playoff",
            "player_on_off",
            ["season", "is_playoff"],
        )


def downgrade():
    if _has_index("player_on_off", "ix_player_on_off_playoff"):
        op.drop_index("ix_player_on_off_playoff", table_name="player_on_off")
    if _has_index("lineup_stats", "ix_lineup_stats_playoff_team"):
        op.drop_index("ix_lineup_stats_playoff_team", table_name="lineup_stats")
