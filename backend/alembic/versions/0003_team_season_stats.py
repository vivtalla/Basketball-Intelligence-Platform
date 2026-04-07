"""Add canonical persisted official team season stats."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0003_team_season_stats"
down_revision = "0002_legacy_schema_drift"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("team_season_stats"):
        return

    op.create_table(
        "team_season_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("is_playoff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="stats.nba.com/team-dashboard"),
        sa.Column("gp", sa.Integer(), nullable=True),
        sa.Column("w", sa.Integer(), nullable=True),
        sa.Column("l", sa.Integer(), nullable=True),
        sa.Column("w_pct", sa.Float(), nullable=True),
        sa.Column("pts_pg", sa.Float(), nullable=True),
        sa.Column("ast_pg", sa.Float(), nullable=True),
        sa.Column("reb_pg", sa.Float(), nullable=True),
        sa.Column("tov_pg", sa.Float(), nullable=True),
        sa.Column("blk_pg", sa.Float(), nullable=True),
        sa.Column("stl_pg", sa.Float(), nullable=True),
        sa.Column("fg_pct", sa.Float(), nullable=True),
        sa.Column("fg3_pct", sa.Float(), nullable=True),
        sa.Column("ft_pct", sa.Float(), nullable=True),
        sa.Column("plus_minus_pg", sa.Float(), nullable=True),
        sa.Column("off_rating", sa.Float(), nullable=True),
        sa.Column("def_rating", sa.Float(), nullable=True),
        sa.Column("net_rating", sa.Float(), nullable=True),
        sa.Column("pace", sa.Float(), nullable=True),
        sa.Column("efg_pct", sa.Float(), nullable=True),
        sa.Column("ts_pct", sa.Float(), nullable=True),
        sa.Column("pie", sa.Float(), nullable=True),
        sa.Column("oreb_pct", sa.Float(), nullable=True),
        sa.Column("dreb_pct", sa.Float(), nullable=True),
        sa.Column("tov_pct", sa.Float(), nullable=True),
        sa.Column("ast_pct", sa.Float(), nullable=True),
        sa.Column("off_rating_rank", sa.Integer(), nullable=True),
        sa.Column("def_rating_rank", sa.Integer(), nullable=True),
        sa.Column("net_rating_rank", sa.Integer(), nullable=True),
        sa.Column("pace_rank", sa.Integer(), nullable=True),
        sa.Column("efg_pct_rank", sa.Integer(), nullable=True),
        sa.Column("ts_pct_rank", sa.Integer(), nullable=True),
        sa.Column("oreb_pct_rank", sa.Integer(), nullable=True),
        sa.Column("tov_pct_rank", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "season", "is_playoff", name="uq_team_season_playoff"),
    )
    op.create_index("ix_team_season_stats_season", "team_season_stats", ["season"])
    op.create_index("ix_team_season_stats_team_season", "team_season_stats", ["team_id", "season"])


def downgrade() -> None:
    if not _has_table("team_season_stats"):
        return
    op.drop_index("ix_team_season_stats_team_season", table_name="team_season_stats")
    op.drop_index("ix_team_season_stats_season", table_name="team_season_stats")
    op.drop_table("team_season_stats")
