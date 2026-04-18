"""Add player gravity and official context tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0005_player_gravity_context"
down_revision = "0004_team_split_stats"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("player_play_type_stats"):
        op.create_table(
            "player_play_type_stats",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("season_type", sa.String(length=30), nullable=False, server_default="Regular Season"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="stats.nba.com/synergy-play-types"),
            sa.Column("play_type", sa.String(length=80), nullable=False),
            sa.Column("type_grouping", sa.String(length=80), nullable=False, server_default="offensive"),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("team_abbreviation", sa.String(length=10), nullable=True),
            sa.Column("gp", sa.Integer(), nullable=True),
            sa.Column("possessions", sa.Float(), nullable=True),
            sa.Column("poss_pct", sa.Float(), nullable=True),
            sa.Column("points", sa.Float(), nullable=True),
            sa.Column("ppp", sa.Float(), nullable=True),
            sa.Column("percentile", sa.Float(), nullable=True),
            sa.Column("fg_pct", sa.Float(), nullable=True),
            sa.Column("efg_pct", sa.Float(), nullable=True),
            sa.Column("tov_poss_pct", sa.Float(), nullable=True),
            sa.Column("score_poss_pct", sa.Float(), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("player_id", "season", "season_type", "play_type", "type_grouping", "source", name="uq_player_play_type_stat"),
        )
        op.create_index("ix_player_play_type_stats_season", "player_play_type_stats", ["season"])
        op.create_index("ix_player_play_type_stats_player_season", "player_play_type_stats", ["player_id", "season"])

    if not _has_table("player_tracking_stats"):
        op.create_table(
            "player_tracking_stats",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("season_type", sa.String(length=30), nullable=False, server_default="Regular Season"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="stats.nba.com/player-tracking"),
            sa.Column("tracking_family", sa.String(length=50), nullable=False),
            sa.Column("split_key", sa.String(length=80), nullable=False, server_default="overall"),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("team_abbreviation", sa.String(length=10), nullable=True),
            sa.Column("gp", sa.Integer(), nullable=True),
            sa.Column("minutes", sa.Float(), nullable=True),
            sa.Column("touches", sa.Float(), nullable=True),
            sa.Column("front_court_touches", sa.Float(), nullable=True),
            sa.Column("time_of_possession", sa.Float(), nullable=True),
            sa.Column("drives", sa.Float(), nullable=True),
            sa.Column("passes_made", sa.Float(), nullable=True),
            sa.Column("passes_received", sa.Float(), nullable=True),
            sa.Column("catch_shoot_fga", sa.Float(), nullable=True),
            sa.Column("catch_shoot_pts", sa.Float(), nullable=True),
            sa.Column("pull_up_fga", sa.Float(), nullable=True),
            sa.Column("pull_up_pts", sa.Float(), nullable=True),
            sa.Column("paint_touch_pts", sa.Float(), nullable=True),
            sa.Column("close_touch_pts", sa.Float(), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("player_id", "season", "season_type", "tracking_family", "split_key", "source", name="uq_player_tracking_stat"),
        )
        op.create_index("ix_player_tracking_stats_season", "player_tracking_stats", ["season"])
        op.create_index("ix_player_tracking_stats_player_season", "player_tracking_stats", ["player_id", "season"])

    if not _has_table("player_hustle_stats"):
        op.create_table(
            "player_hustle_stats",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("season_type", sa.String(length=30), nullable=False, server_default="Regular Season"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="stats.nba.com/league-hustle"),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("team_abbreviation", sa.String(length=10), nullable=True),
            sa.Column("gp", sa.Integer(), nullable=True),
            sa.Column("minutes", sa.Float(), nullable=True),
            sa.Column("contested_shots", sa.Float(), nullable=True),
            sa.Column("deflections", sa.Float(), nullable=True),
            sa.Column("charges_drawn", sa.Float(), nullable=True),
            sa.Column("screen_assists", sa.Float(), nullable=True),
            sa.Column("screen_assist_points", sa.Float(), nullable=True),
            sa.Column("loose_balls_recovered", sa.Float(), nullable=True),
            sa.Column("box_outs", sa.Float(), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("player_id", "season", "season_type", "source", name="uq_player_hustle_stat"),
        )
        op.create_index("ix_player_hustle_stats_season", "player_hustle_stats", ["season"])
        op.create_index("ix_player_hustle_stats_player_season", "player_hustle_stats", ["player_id", "season"])

    if not _has_table("player_gravity_stats"):
        op.create_table(
            "player_gravity_stats",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("season_type", sa.String(length=30), nullable=False, server_default="Regular Season"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="courtvue_proxy"),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("team_abbreviation", sa.String(length=10), nullable=True),
            sa.Column("gravity_minutes", sa.Float(), nullable=True),
            sa.Column("overall_gravity", sa.Float(), nullable=True),
            sa.Column("shooting_gravity", sa.Float(), nullable=True),
            sa.Column("rim_gravity", sa.Float(), nullable=True),
            sa.Column("creation_gravity", sa.Float(), nullable=True),
            sa.Column("roll_or_screen_gravity", sa.Float(), nullable=True),
            sa.Column("off_ball_gravity", sa.Float(), nullable=True),
            sa.Column("spacing_lift", sa.Float(), nullable=True),
            sa.Column("on_ball_perimeter_gravity", sa.Float(), nullable=True),
            sa.Column("off_ball_perimeter_gravity", sa.Float(), nullable=True),
            sa.Column("on_ball_interior_gravity", sa.Float(), nullable=True),
            sa.Column("off_ball_interior_gravity", sa.Float(), nullable=True),
            sa.Column("gravity_confidence", sa.String(length=20), nullable=False, server_default="low"),
            sa.Column("source_note", sa.String(length=500), nullable=True),
            sa.Column("warnings", sa.JSON(), nullable=True),
            sa.Column("raw_payload", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("player_id", "season", "season_type", "source", name="uq_player_gravity_stat"),
        )
        op.create_index("ix_player_gravity_stats_season", "player_gravity_stats", ["season"])
        op.create_index("ix_player_gravity_stats_player_season", "player_gravity_stats", ["player_id", "season"])


def downgrade() -> None:
    for table, indexes in [
        ("player_gravity_stats", ["ix_player_gravity_stats_player_season", "ix_player_gravity_stats_season"]),
        ("player_hustle_stats", ["ix_player_hustle_stats_player_season", "ix_player_hustle_stats_season"]),
        ("player_tracking_stats", ["ix_player_tracking_stats_player_season", "ix_player_tracking_stats_season"]),
        ("player_play_type_stats", ["ix_player_play_type_stats_player_season", "ix_player_play_type_stats_season"]),
    ]:
        if _has_table(table):
            for index in indexes:
                op.drop_index(index, table_name=table)
            op.drop_table(table)
