"""Sprint 52 — MVP holistic case engine tables.

Adds:
- external_metrics_meta JSON column on season_stats (attribution for EPM/LEBRON/RAPTOR/PIPM/DARKO/RAPM)
- player_clutch_stats — league dashboard clutch signals (minutes, net rating, TS%, on/off, close W-L)
- player_opponent_splits — opponent-bucketed production for opponent-adjusted scoring
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0006_mvp_impact_and_clutch"
down_revision = "0005_player_gravity_context"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("season_stats", "external_metrics_meta"):
        op.add_column(
            "season_stats",
            sa.Column("external_metrics_meta", sa.JSON(), nullable=True),
        )

    if not _has_table("player_clutch_stats"):
        op.create_table(
            "player_clutch_stats",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("season_type", sa.String(length=30), nullable=False, server_default="Regular Season"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="stats.nba.com/leaguedashplayerclutch"),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("team_abbreviation", sa.String(length=10), nullable=True),
            sa.Column("clutch_games", sa.Integer(), nullable=True),
            sa.Column("clutch_minutes", sa.Float(), nullable=True),
            sa.Column("clutch_possessions", sa.Float(), nullable=True),
            sa.Column("clutch_pts", sa.Float(), nullable=True),
            sa.Column("clutch_fgm", sa.Float(), nullable=True),
            sa.Column("clutch_fga", sa.Float(), nullable=True),
            sa.Column("clutch_fg_pct", sa.Float(), nullable=True),
            sa.Column("clutch_fg3m", sa.Float(), nullable=True),
            sa.Column("clutch_fg3a", sa.Float(), nullable=True),
            sa.Column("clutch_ts_pct", sa.Float(), nullable=True),
            sa.Column("clutch_efg_pct", sa.Float(), nullable=True),
            sa.Column("clutch_ast", sa.Float(), nullable=True),
            sa.Column("clutch_tov", sa.Float(), nullable=True),
            sa.Column("clutch_ast_to", sa.Float(), nullable=True),
            sa.Column("clutch_usg_pct", sa.Float(), nullable=True),
            sa.Column("clutch_plus_minus", sa.Float(), nullable=True),
            sa.Column("clutch_net_rating", sa.Float(), nullable=True),
            sa.Column("clutch_on_off", sa.Float(), nullable=True),
            sa.Column("close_game_wins", sa.Integer(), nullable=True),
            sa.Column("close_game_losses", sa.Integer(), nullable=True),
            sa.Column("confidence", sa.String(length=20), nullable=False, server_default="low"),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "player_id", "season", "season_type", "source",
                name="uq_player_clutch_stat",
            ),
        )
        op.create_index("ix_player_clutch_stats_season", "player_clutch_stats", ["season"])
        op.create_index("ix_player_clutch_stats_player_season", "player_clutch_stats", ["player_id", "season"])

    if not _has_table("player_opponent_splits"):
        op.create_table(
            "player_opponent_splits",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("season_type", sa.String(length=30), nullable=False, server_default="Regular Season"),
            sa.Column("opponent_bucket", sa.String(length=30), nullable=False),
            sa.Column("bucket_label", sa.String(length=80), nullable=True),
            sa.Column("games", sa.Integer(), nullable=True),
            sa.Column("minutes", sa.Float(), nullable=True),
            sa.Column("pts_per_game", sa.Float(), nullable=True),
            sa.Column("reb_per_game", sa.Float(), nullable=True),
            sa.Column("ast_per_game", sa.Float(), nullable=True),
            sa.Column("ts_pct", sa.Float(), nullable=True),
            sa.Column("efg_pct", sa.Float(), nullable=True),
            sa.Column("plus_minus", sa.Float(), nullable=True),
            sa.Column("confidence", sa.String(length=20), nullable=False, server_default="low"),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "player_id", "season", "season_type", "opponent_bucket",
                name="uq_player_opponent_split",
            ),
        )
        op.create_index("ix_player_opponent_splits_season", "player_opponent_splits", ["season"])
        op.create_index(
            "ix_player_opponent_splits_player_season",
            "player_opponent_splits",
            ["player_id", "season"],
        )


def downgrade() -> None:
    if _has_table("player_opponent_splits"):
        op.drop_index("ix_player_opponent_splits_player_season", table_name="player_opponent_splits")
        op.drop_index("ix_player_opponent_splits_season", table_name="player_opponent_splits")
        op.drop_table("player_opponent_splits")

    if _has_table("player_clutch_stats"):
        op.drop_index("ix_player_clutch_stats_player_season", table_name="player_clutch_stats")
        op.drop_index("ix_player_clutch_stats_season", table_name="player_clutch_stats")
        op.drop_table("player_clutch_stats")

    if _has_column("season_stats", "external_metrics_meta"):
        op.drop_column("season_stats", "external_metrics_meta")
