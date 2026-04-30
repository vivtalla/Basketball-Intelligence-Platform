"""Sprint 81 — player_split_stats + play_type_stats.

Closes the two highest-priority gaps from `specs/official-data-source-matrix.md`:
- Player split dashboards (LeagueDashPlayerStats split families)
- Play type stats (Synergy-style PlayTypeStats per archetype)

Both are persisted-DB-first reads. Sync functions write nightly via
``daily_sync.sh``. Frontend renders defer to Sprint 82.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0020_sprint81_pl_splits_pt"
down_revision = "0019_sprint81_award_cands"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("player_split_stats"):
        op.create_table(
            "player_split_stats",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=False),
            sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=True),
            sa.Column("season", sa.String(10), nullable=False),
            sa.Column("is_playoff", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("split_family", sa.String(50), nullable=False),
            sa.Column("split_value", sa.String(80), nullable=False),
            sa.Column("label", sa.String(120), nullable=False),
            sa.Column("source", sa.String(70), nullable=False, server_default="stats.nba.com/player-general-splits"),
            sa.Column("gp", sa.Integer, server_default="0"),
            sa.Column("w", sa.Integer, server_default="0"),
            sa.Column("l", sa.Integer, server_default="0"),
            sa.Column("w_pct", sa.Float, server_default="0"),
            sa.Column("min", sa.Float),
            sa.Column("pts", sa.Float),
            sa.Column("reb", sa.Float),
            sa.Column("ast", sa.Float),
            sa.Column("tov", sa.Float),
            sa.Column("stl", sa.Float),
            sa.Column("blk", sa.Float),
            sa.Column("fg_pct", sa.Float),
            sa.Column("fg3_pct", sa.Float),
            sa.Column("ft_pct", sa.Float),
            sa.Column("ts_pct", sa.Float),
            sa.Column("usg_pct", sa.Float),
            sa.Column("plus_minus", sa.Float),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "player_id", "season", "is_playoff", "split_family", "split_value",
                name="uq_player_split_stat",
            ),
        )
        op.create_index("ix_player_split_stats_player_season", "player_split_stats", ["player_id", "season"])
        op.create_index("ix_player_split_stats_family", "player_split_stats", ["split_family"])

    if not _has_table("play_type_stats"):
        op.create_table(
            "play_type_stats",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=False),
            sa.Column("team_id", sa.Integer, sa.ForeignKey("teams.id"), nullable=True),
            sa.Column("season", sa.String(10), nullable=False),
            sa.Column("is_playoff", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.Column("play_type", sa.String(40), nullable=False),
            sa.Column("play_role", sa.String(40), nullable=False, server_default="primary"),
            sa.Column("source", sa.String(70), nullable=False, server_default="stats.nba.com/playtype"),
            sa.Column("gp", sa.Integer, server_default="0"),
            sa.Column("poss", sa.Integer, server_default="0"),
            sa.Column("poss_pct", sa.Float),
            sa.Column("pts", sa.Float),
            sa.Column("fgm", sa.Float),
            sa.Column("fga", sa.Float),
            sa.Column("fg_pct", sa.Float),
            sa.Column("efg_pct", sa.Float),
            sa.Column("ts_pct", sa.Float),
            sa.Column("ftm", sa.Float),
            sa.Column("fta", sa.Float),
            sa.Column("ft_pct", sa.Float),
            sa.Column("ppp", sa.Float),
            sa.Column("percentile", sa.Float),
            sa.Column("score_freq_pct", sa.Float),
            sa.Column("sf_freq_pct", sa.Float),
            sa.Column("tov_freq_pct", sa.Float),
            sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
            sa.UniqueConstraint(
                "player_id", "season", "is_playoff", "play_type", "play_role",
                name="uq_play_type_stat",
            ),
        )
        op.create_index("ix_play_type_stats_player_season", "play_type_stats", ["player_id", "season"])
        op.create_index("ix_play_type_stats_play_type", "play_type_stats", ["play_type"])


def downgrade() -> None:
    if _has_table("play_type_stats"):
        op.drop_index("ix_play_type_stats_play_type", table_name="play_type_stats")
        op.drop_index("ix_play_type_stats_player_season", table_name="play_type_stats")
        op.drop_table("play_type_stats")
    if _has_table("player_split_stats"):
        op.drop_index("ix_player_split_stats_family", table_name="player_split_stats")
        op.drop_index("ix_player_split_stats_player_season", table_name="player_split_stats")
        op.drop_table("player_split_stats")
