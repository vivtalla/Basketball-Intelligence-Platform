"""Sprint 86 Stream C — team-level tracking + hustle dashboards.

Mirrors Sprint 5 Player Tracking + Hustle tables (`player_tracking_stats`,
`player_hustle_stats`) at the team level. New tables ``team_tracking_stats``
and ``team_hustle_stats`` are keyed on ``team_id`` (FK -> ``teams.id``)
instead of ``player_id``. Same column inventory, indexes, and unique-key
shape; no behavioural data migration on upgrade.

Reversible: ``downgrade()`` drops both tables in reverse-create order with
their indexes.

Defensive guards (Sprint 85 lesson — legacy-baseline test path stamps to a
schema that lacks ``teams``): only emit FK constraints when the parent
table exists. Index + table creation are also no-ops if a previous run
left the table in place.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0022_sprint86_team_track_hus"
down_revision = "0021_sprint85_bracket_advance"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    names = {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table_name)}
    return index_name in names


def _fk_constraints():
    """Build FK constraints only when the parent ``teams`` table is present.

    Returns a list of constraint args ready to splat into ``op.create_table``.
    """
    if _has_table("teams"):
        return [sa.ForeignKeyConstraint(["team_id"], ["teams.id"])]
    return []


def upgrade() -> None:
    if not _has_table("team_tracking_stats"):
        op.create_table(
            "team_tracking_stats",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column(
                "season_type",
                sa.String(length=30),
                nullable=False,
                server_default="Regular Season",
            ),
            sa.Column(
                "source",
                sa.String(length=80),
                nullable=False,
                server_default="stats.nba.com/team-tracking",
            ),
            sa.Column("tracking_family", sa.String(length=50), nullable=False),
            sa.Column(
                "split_key",
                sa.String(length=80),
                nullable=False,
                server_default="overall",
            ),
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
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=True,
            ),
            *_fk_constraints(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "team_id",
                "season",
                "season_type",
                "tracking_family",
                "split_key",
                "source",
                name="uq_team_tracking_stat",
            ),
        )
        op.create_index(
            "ix_team_tracking_stats_season",
            "team_tracking_stats",
            ["season"],
        )
        op.create_index(
            "ix_team_tracking_stats_team_season",
            "team_tracking_stats",
            ["team_id", "season"],
        )

    if not _has_table("team_hustle_stats"):
        op.create_table(
            "team_hustle_stats",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("team_id", sa.Integer(), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column(
                "season_type",
                sa.String(length=30),
                nullable=False,
                server_default="Regular Season",
            ),
            sa.Column(
                "source",
                sa.String(length=80),
                nullable=False,
                server_default="stats.nba.com/league-hustle-team",
            ),
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
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=True,
            ),
            *_fk_constraints(),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "team_id",
                "season",
                "season_type",
                "source",
                name="uq_team_hustle_stat",
            ),
        )
        op.create_index(
            "ix_team_hustle_stats_season",
            "team_hustle_stats",
            ["season"],
        )
        op.create_index(
            "ix_team_hustle_stats_team_season",
            "team_hustle_stats",
            ["team_id", "season"],
        )


def downgrade() -> None:
    for table, indexes in [
        (
            "team_hustle_stats",
            ["ix_team_hustle_stats_team_season", "ix_team_hustle_stats_season"],
        ),
        (
            "team_tracking_stats",
            ["ix_team_tracking_stats_team_season", "ix_team_tracking_stats_season"],
        ),
    ]:
        if _has_table(table):
            for index in indexes:
                if _has_index(table, index):
                    op.drop_index(index, table_name=table)
            op.drop_table(table)
