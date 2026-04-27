"""Sprint 69 — player analysis contexts.

Persist manual analyst context windows that affect interpretation labels without
changing raw stat storage. Automatic injury-report contexts remain derived from
player_injuries at read time.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0011_player_analysis_contexts"
down_revision = "0010_pre_read_packet_metadata"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("player_analysis_contexts"):
        op.create_table(
            "player_analysis_contexts",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("context_type", sa.String(length=40), nullable=False),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("severity", sa.String(length=20), nullable=True),
            sa.Column("source", sa.String(length=40), nullable=False, server_default="manual"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("applies_to", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_player_analysis_contexts_player_season",
            "player_analysis_contexts",
            ["player_id", "season"],
        )
        op.create_index(
            "ix_player_analysis_contexts_dates",
            "player_analysis_contexts",
            ["start_date", "end_date"],
        )


def downgrade() -> None:
    if _has_table("player_analysis_contexts"):
        op.drop_index("ix_player_analysis_contexts_dates", table_name="player_analysis_contexts")
        op.drop_index("ix_player_analysis_contexts_player_season", table_name="player_analysis_contexts")
        op.drop_table("player_analysis_contexts")
