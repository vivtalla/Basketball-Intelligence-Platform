"""Sprint 79 Stream A1 — award_voting table for mvp_case_v5 calibration.

One row per (player_id, season, award_type, ballot_position). Powers the
coordinate-descent fit of Award Case modifier weights against historical
voting outcomes.

Methodology spec: ``specs/methodology-future-modeling.md#1``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0016_sprint79_award_voting"
down_revision = "0015_sprint79_role_expansion"
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
    if not _has_table("award_voting"):
        op.create_table(
            "award_voting",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("award_type", sa.String(length=10), nullable=False),  # MVP, DPOY, MIP, 6MOY
            sa.Column("ballot_position", sa.Integer(), nullable=True),  # NULL = not on ballot
            sa.Column("voter_count", sa.Integer(), nullable=False),
            sa.Column("total_award_points", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=40), server_default="basketball_reference"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint(
                "player_id", "season", "award_type", "ballot_position",
                name="uq_award_voting",
            ),
        )
    _safe_create_index(
        "ix_award_voting_season_award",
        "award_voting",
        ["season", "award_type"],
    )


def downgrade():
    if _has_index("award_voting", "ix_award_voting_season_award"):
        op.drop_index("ix_award_voting_season_award", table_name="award_voting")
    if _has_table("award_voting"):
        op.drop_table("award_voting")
