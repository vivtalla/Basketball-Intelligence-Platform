"""Add canonical persisted official team general split stats."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0004_team_split_stats"
down_revision = "0003_team_season_stats"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("team_split_stats"):
        return

    op.create_table(
        "team_split_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("is_playoff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("split_family", sa.String(length=50), nullable=False),
        sa.Column("split_value", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=60), nullable=False, server_default="stats.nba.com/team-general-splits"),
        sa.Column("gp", sa.Integer(), nullable=True),
        sa.Column("w", sa.Integer(), nullable=True),
        sa.Column("l", sa.Integer(), nullable=True),
        sa.Column("w_pct", sa.Float(), nullable=True),
        sa.Column("min", sa.Float(), nullable=True),
        sa.Column("pts", sa.Float(), nullable=True),
        sa.Column("reb", sa.Float(), nullable=True),
        sa.Column("ast", sa.Float(), nullable=True),
        sa.Column("tov", sa.Float(), nullable=True),
        sa.Column("stl", sa.Float(), nullable=True),
        sa.Column("blk", sa.Float(), nullable=True),
        sa.Column("fg_pct", sa.Float(), nullable=True),
        sa.Column("fg3_pct", sa.Float(), nullable=True),
        sa.Column("ft_pct", sa.Float(), nullable=True),
        sa.Column("plus_minus", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "season",
            "is_playoff",
            "split_family",
            "split_value",
            name="uq_team_split_stat",
        ),
    )
    op.create_index("ix_team_split_stats_season", "team_split_stats", ["season"])
    op.create_index("ix_team_split_stats_team_season", "team_split_stats", ["team_id", "season"])
    op.create_index("ix_team_split_stats_family", "team_split_stats", ["split_family"])


def downgrade() -> None:
    if not _has_table("team_split_stats"):
        return
    op.drop_index("ix_team_split_stats_family", table_name="team_split_stats")
    op.drop_index("ix_team_split_stats_team_season", table_name="team_split_stats")
    op.drop_index("ix_team_split_stats_season", table_name="team_split_stats")
    op.drop_table("team_split_stats")
