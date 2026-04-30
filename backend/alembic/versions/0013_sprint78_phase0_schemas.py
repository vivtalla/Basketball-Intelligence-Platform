"""Sprint 78 Phase 0 — schema kickoff for the 10-team parallel sprint.

Adds eight new tables that back the Sprint 78 feature teams:

- ``player_contracts`` (FO1 Trade Machine, FO2 FA Workspace, FO4 Multi-Year)
- ``draft_prospects`` + ``draft_prospect_stats`` + ``draft_prospect_measurements`` (FO3)
- ``draft_pick_assets`` (FO4)
- ``player_injury_history`` (FO5 Injury Duration Model)
- ``player_streaks`` + ``milestone_snapshots`` (CF5 Streaks & Milestones)

This migration is idempotent so it can run cleanly against legacy schemas
where ``Base.metadata.create_all`` already created the tables (e.g., fresh
SQLite test databases).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0013_sprint78_phase0_schemas"
down_revision = "0012_playoffs_data_layer"
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
    if not _has_table("player_contracts"):
        op.create_table(
            "player_contracts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("salary", sa.Integer(), nullable=False),
            sa.Column("years_remaining", sa.Integer(), server_default="1"),
            sa.Column("is_player_option", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("is_team_option", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("is_non_guaranteed", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("no_trade_clause", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("contract_type", sa.String(length=20)),
            sa.Column("signed_on", sa.Date()),
            sa.Column("expires_on", sa.Date()),
            sa.Column("source", sa.String(length=40), server_default="spotrac"),
            sa.Column("source_url", sa.Text()),
            sa.Column("last_synced_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("player_id", "season", name="uq_player_contract_player_season"),
        )
    _safe_create_index("ix_player_contracts_player", "player_contracts", ["player_id"])
    _safe_create_index("ix_player_contracts_season", "player_contracts", ["season"])
    _safe_create_index("ix_player_contracts_team", "player_contracts", ["team_id"])

    if not _has_table("draft_prospects"):
        op.create_table(
            "draft_prospects",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("external_id", sa.String(length=80), nullable=False),
            sa.Column("full_name", sa.String(length=120), nullable=False),
            sa.Column("draft_year", sa.Integer(), nullable=False),
            sa.Column("age_on_draft_day", sa.Float()),
            sa.Column("height_inches", sa.Float()),
            sa.Column("weight_lbs", sa.Float()),
            sa.Column("primary_position", sa.String(length=10)),
            sa.Column("school", sa.String(length=120)),
            sa.Column("school_type", sa.String(length=20)),
            sa.Column("consensus_rank", sa.Integer()),
            sa.Column("consensus_sources", sa.JSON()),
            sa.Column("nba_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
            sa.Column("headshot_url", sa.String(length=300)),
            sa.Column("bio", sa.Text()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("draft_year", "external_id", name="uq_draft_prospect_year_extid"),
        )
    _safe_create_index("ix_draft_prospects_year", "draft_prospects", ["draft_year"])
    _safe_create_index("ix_draft_prospects_consensus", "draft_prospects", ["consensus_rank"])

    if not _has_table("draft_prospect_stats"):
        op.create_table(
            "draft_prospect_stats",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("draft_prospects.id"), nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("league", sa.String(length=40), nullable=False),
            sa.Column("team_name", sa.String(length=120)),
            sa.Column("gp", sa.Integer()),
            sa.Column("min_pg", sa.Float()),
            sa.Column("pts_pg", sa.Float()),
            sa.Column("reb_pg", sa.Float()),
            sa.Column("ast_pg", sa.Float()),
            sa.Column("stl_pg", sa.Float()),
            sa.Column("blk_pg", sa.Float()),
            sa.Column("tov_pg", sa.Float()),
            sa.Column("fg_pct", sa.Float()),
            sa.Column("fg3_pct", sa.Float()),
            sa.Column("ft_pct", sa.Float()),
            sa.Column("ts_pct", sa.Float()),
            sa.Column("usg_pct", sa.Float()),
            sa.Column("pace", sa.Float()),
            sa.Column("source", sa.String(length=40), server_default="sports_reference"),
            sa.Column("last_synced_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("prospect_id", "season", "league", name="uq_dp_stat_prospect_season_league"),
        )
    _safe_create_index("ix_dp_stats_prospect", "draft_prospect_stats", ["prospect_id"])

    if not _has_table("draft_prospect_measurements"):
        op.create_table(
            "draft_prospect_measurements",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prospect_id", sa.Integer(), sa.ForeignKey("draft_prospects.id"), nullable=False),
            sa.Column("height_no_shoes", sa.Float()),
            sa.Column("height_with_shoes", sa.Float()),
            sa.Column("weight", sa.Float()),
            sa.Column("wingspan", sa.Float()),
            sa.Column("standing_reach", sa.Float()),
            sa.Column("body_fat_pct", sa.Float()),
            sa.Column("hand_length", sa.Float()),
            sa.Column("hand_width", sa.Float()),
            sa.Column("standing_vert", sa.Float()),
            sa.Column("max_vert", sa.Float()),
            sa.Column("lane_agility_seconds", sa.Float()),
            sa.Column("three_quarter_sprint_seconds", sa.Float()),
            sa.Column("bench_press_135", sa.Integer()),
            sa.Column("measured_on", sa.Date()),
            sa.Column("source", sa.String(length=40), server_default="nba_combine"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    _safe_create_index("ix_dp_measurements_prospect", "draft_prospect_measurements", ["prospect_id"])

    if not _has_table("draft_pick_assets"):
        op.create_table(
            "draft_pick_assets",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("draft_year", sa.Integer(), nullable=False),
            sa.Column("round", sa.Integer(), nullable=False),
            sa.Column("owner_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
            sa.Column("origin_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
            sa.Column("is_swap", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("is_conveyed", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("protection_summary", sa.String(length=200)),
            sa.Column("expected_slot_low", sa.Integer()),
            sa.Column("expected_slot_high", sa.Integer()),
            sa.Column("note", sa.Text()),
            sa.Column("source", sa.String(length=40), server_default="manual"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        )
    _safe_create_index("ix_dp_assets_owner", "draft_pick_assets", ["owner_team_id"])
    _safe_create_index("ix_dp_assets_year", "draft_pick_assets", ["draft_year"])

    if not _has_table("player_injury_history"):
        op.create_table(
            "player_injury_history",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("season", sa.String(length=10)),
            sa.Column("body_part", sa.String(length=60)),
            sa.Column("severity", sa.String(length=20)),
            sa.Column("diagnosis", sa.String(length=200)),
            sa.Column("started_on", sa.Date(), nullable=False),
            sa.Column("resolved_on", sa.Date()),
            sa.Column("games_missed", sa.Integer()),
            sa.Column("age_at_start", sa.Float()),
            sa.Column("is_recurring", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("source", sa.String(length=40), server_default="prosportstransactions"),
            sa.Column("source_url", sa.Text()),
            sa.Column("last_synced_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    _safe_create_index("ix_pih_player", "player_injury_history", ["player_id"])
    _safe_create_index("ix_pih_started", "player_injury_history", ["started_on"])
    _safe_create_index("ix_pih_body_part", "player_injury_history", ["body_part"])

    if not _has_table("player_streaks"):
        op.create_table(
            "player_streaks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("streak_type", sa.String(length=40), nullable=False),
            sa.Column("length", sa.Integer(), nullable=False),
            sa.Column("started_on", sa.Date()),
            sa.Column("last_game_on", sa.Date()),
            sa.Column("last_game_id", sa.String(length=20)),
            sa.Column("threshold", sa.JSON()),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("season", sa.String(length=10)),
            sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("player_id", "streak_type", name="uq_player_streak_type"),
        )
    _safe_create_index("ix_player_streaks_type", "player_streaks", ["streak_type"])
    _safe_create_index("ix_player_streaks_length", "player_streaks", ["length"])

    if not _has_table("milestone_snapshots"):
        op.create_table(
            "milestone_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
            sa.Column("milestone_key", sa.String(length=40), nullable=False),
            sa.Column("threshold", sa.Integer(), nullable=False),
            sa.Column("current_value", sa.Float(), nullable=False),
            sa.Column("games_to_milestone", sa.Integer()),
            sa.Column("achieved_on", sa.Date()),
            sa.Column("achieved_in_game_id", sa.String(length=20)),
            sa.Column("season", sa.String(length=10)),
            sa.Column("is_career_milestone", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("computed_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("player_id", "milestone_key", name="uq_milestone_player_key"),
        )
    _safe_create_index("ix_milestones_player", "milestone_snapshots", ["player_id"])
    _safe_create_index("ix_milestones_key", "milestone_snapshots", ["milestone_key"])
    _safe_create_index("ix_milestones_proximity", "milestone_snapshots", ["games_to_milestone"])


def downgrade():
    op.drop_table("milestone_snapshots")
    op.drop_table("player_streaks")
    op.drop_table("player_injury_history")
    op.drop_table("draft_pick_assets")
    op.drop_table("draft_prospect_measurements")
    op.drop_table("draft_prospect_stats")
    op.drop_table("draft_prospects")
    op.drop_table("player_contracts")
