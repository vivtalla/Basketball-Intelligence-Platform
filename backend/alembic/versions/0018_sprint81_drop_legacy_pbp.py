"""Sprint 81 — drop legacy play_by_play table.

The legacy ``play_by_play`` table was the original PBP storage from Sprint
~5; ``play_by_play_events`` superseded it in Sprint 77's PBP rewrite.
Sprint 81 finishes the migration by:

- migrating all readers to ``PlayByPlayEvent``
- halting writes to ``play_by_play`` from ``warehouse_service`` and
  ``pbp_sync_service``
- removing the ORM model + GameLog.play_by_play relationship
- dropping the table here, freeing ~677 MB on the Hetzner VM.

Idempotent: only drops when present so re-runs against fresh DBs are safe.

Run ``VACUUM FULL`` manually after this migration to reclaim the bytes:
    psql $DATABASE_URL -c 'VACUUM FULL;'
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0018_sprint81_drop_legacy_pbp"
down_revision = "0017_sprint80_raw_payload_ttl"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("play_by_play"):
        return
    op.drop_table("play_by_play")


def downgrade() -> None:
    # Recreate the legacy schema for emergency rollback. This does not
    # restore data — the rows are gone. Use a backup restore if you need
    # the historical events back.
    if _has_table("play_by_play"):
        return
    op.create_table(
        "play_by_play",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("game_id", sa.String(10), sa.ForeignKey("game_logs.game_id"), nullable=False),
        sa.Column("action_number", sa.Integer, nullable=False),
        sa.Column("period", sa.Integer),
        sa.Column("clock", sa.String(20)),
        sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=True),
        sa.Column("action_type", sa.String(50)),
        sa.Column("sub_type", sa.String(50)),
        sa.Column("description", sa.String(500)),
        sa.Column("score_home", sa.Integer),
        sa.Column("score_away", sa.Integer),
        sa.UniqueConstraint("game_id", "action_number", name="uq_pbp_game_action"),
    )
    op.create_index("ix_pbp_player_game", "play_by_play", ["player_id", "game_id"])
    op.create_index("ix_pbp_game_action_type", "play_by_play", ["game_id", "action_type"])
