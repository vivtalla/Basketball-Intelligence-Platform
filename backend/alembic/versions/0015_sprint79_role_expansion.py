"""Sprint 79 Stream A2 — role_expansion_observations table for opportunity_v2.

Materializes the latent dataset already in season_stats: every (player_id, season)
pair where usg_pct grew >= +0.03 over the prior season AND both seasons have
GP >= 40, with covariates (pre_ts_pct, pre_ast_rate, pre_obpm, pre_age,
pre_role_archetype) and the outcome variable (ts_delta).

Idempotent: ``UniqueConstraint(player_id, from_season, to_season)`` makes re-runs
no-ops at the DB level. The materialization service (run via daily_sync.sh)
handles the upsert semantics.

Methodology spec: ``specs/methodology-future-modeling.md#2``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0015_sprint79_role_expansion"
down_revision = "0014_sprint79_playoff_indexes"
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
    if not _has_table("role_expansion_observations"):
        op.create_table(
            "role_expansion_observations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("from_season", sa.String(length=10), nullable=False),
            sa.Column("to_season", sa.String(length=10), nullable=False),
            sa.Column("usg_delta", sa.Float(), nullable=False),
            sa.Column("pre_ts_pct", sa.Float(), nullable=False),
            sa.Column("post_ts_pct", sa.Float(), nullable=False),
            sa.Column("ts_delta", sa.Float(), nullable=False),
            sa.Column("pre_ast_rate", sa.Float(), nullable=True),
            sa.Column("pre_obpm", sa.Float(), nullable=True),
            sa.Column("pre_age", sa.Integer(), nullable=True),
            sa.Column("pre_role_archetype", sa.String(length=40), nullable=True),
            sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint(
                "player_id", "from_season", "to_season",
                name="uq_role_expansion_pair",
            ),
        )
    _safe_create_index(
        "ix_role_expansion_archetype",
        "role_expansion_observations",
        ["pre_role_archetype", "pre_ts_pct"],
    )


def downgrade():
    if _has_index("role_expansion_observations", "ix_role_expansion_archetype"):
        op.drop_index("ix_role_expansion_archetype", table_name="role_expansion_observations")
    if _has_table("role_expansion_observations"):
        op.drop_table("role_expansion_observations")
