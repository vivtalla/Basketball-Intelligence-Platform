"""Add canonical persisted official team shooting split stats."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0009_team_shooting_split_stats"
down_revision = "0008_shot_quality_baselines"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if _has_table("team_shooting_split_stats"):
        return

    op.create_table(
        "team_shooting_split_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("season", sa.String(length=10), nullable=False),
        sa.Column("is_playoff", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("split_family", sa.String(length=60), nullable=False),
        sa.Column("split_value", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("source", sa.String(length=70), nullable=False, server_default="stats.nba.com/team-shooting-splits"),
        sa.Column("fgm", sa.Float(), nullable=True),
        sa.Column("fga", sa.Float(), nullable=True),
        sa.Column("fg_pct", sa.Float(), nullable=True),
        sa.Column("fg3m", sa.Float(), nullable=True),
        sa.Column("fg3a", sa.Float(), nullable=True),
        sa.Column("fg3_pct", sa.Float(), nullable=True),
        sa.Column("efg_pct", sa.Float(), nullable=True),
        sa.Column("blka", sa.Float(), nullable=True),
        sa.Column("pct_ast_2pm", sa.Float(), nullable=True),
        sa.Column("pct_uast_2pm", sa.Float(), nullable=True),
        sa.Column("pct_ast_3pm", sa.Float(), nullable=True),
        sa.Column("pct_uast_3pm", sa.Float(), nullable=True),
        sa.Column("pct_ast_fgm", sa.Float(), nullable=True),
        sa.Column("pct_uast_fgm", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "team_id",
            "season",
            "is_playoff",
            "split_family",
            "split_value",
            name="uq_team_shooting_split_stat",
        ),
    )
    op.create_index(
        "ix_team_shooting_split_stats_season",
        "team_shooting_split_stats",
        ["season"],
    )
    op.create_index(
        "ix_team_shooting_split_stats_team_season",
        "team_shooting_split_stats",
        ["team_id", "season"],
    )
    op.create_index(
        "ix_team_shooting_split_stats_family",
        "team_shooting_split_stats",
        ["split_family"],
    )


def downgrade() -> None:
    if not _has_table("team_shooting_split_stats"):
        return
    op.drop_index("ix_team_shooting_split_stats_family", table_name="team_shooting_split_stats")
    op.drop_index("ix_team_shooting_split_stats_team_season", table_name="team_shooting_split_stats")
    op.drop_index("ix_team_shooting_split_stats_season", table_name="team_shooting_split_stats")
    op.drop_table("team_shooting_split_stats")
