"""Sprint 53 — MVP race timeline snapshots.

Persist daily MVP race outputs so the product can show rank and score movement
without recomputing historical states from mutable aggregate rows.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0007_mvp_race_timeline"
down_revision = "0006_mvp_impact_and_clutch"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("mvp_race_snapshots"):
        op.create_table(
            "mvp_race_snapshots",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column("as_of_date", sa.Date(), nullable=True),
            sa.Column("profile", sa.String(length=40), nullable=False),
            sa.Column("min_gp", sa.Integer(), nullable=False, server_default="20"),
            sa.Column("top", sa.Integer(), nullable=False, server_default="15"),
            sa.Column("scoring_profile", sa.String(length=80), nullable=False, server_default=""),
            sa.Column("payload_summary", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "season",
                "snapshot_date",
                "profile",
                "min_gp",
                name="uq_mvp_race_snapshot_run",
            ),
        )
        op.create_index(
            "ix_mvp_race_snapshots_season_profile_date",
            "mvp_race_snapshots",
            ["season", "profile", "snapshot_date"],
        )

    if not _has_table("mvp_race_snapshot_candidates"):
        op.create_table(
            "mvp_race_snapshot_candidates",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("snapshot_id", sa.Integer(), nullable=False),
            sa.Column("player_id", sa.Integer(), nullable=False),
            sa.Column("player_name", sa.String(length=100), nullable=False, server_default=""),
            sa.Column("team_abbreviation", sa.String(length=10), nullable=False, server_default=""),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("composite_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("context_adjusted_score", sa.Float(), nullable=True),
            sa.Column("momentum", sa.String(length=20), nullable=False, server_default="steady"),
            sa.Column("eligibility_status", sa.String(length=20), nullable=False, server_default="unknown"),
            sa.Column("impact_consensus_score", sa.Float(), nullable=True),
            sa.Column("clutch_confidence", sa.String(length=20), nullable=True),
            sa.Column("gravity_score", sa.Float(), nullable=True),
            sa.Column("coverage_warning_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("pillar_scores", sa.JSON(), nullable=True),
            sa.Column("case_summary", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
            sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
            sa.ForeignKeyConstraint(["snapshot_id"], ["mvp_race_snapshots.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("snapshot_id", "player_id", name="uq_mvp_race_snapshot_candidate"),
        )
        op.create_index(
            "ix_mvp_snapshot_candidates_snapshot_rank",
            "mvp_race_snapshot_candidates",
            ["snapshot_id", "rank"],
        )
        op.create_index(
            "ix_mvp_snapshot_candidates_player",
            "mvp_race_snapshot_candidates",
            ["player_id"],
        )


def downgrade() -> None:
    if _has_table("mvp_race_snapshot_candidates"):
        op.drop_index("ix_mvp_snapshot_candidates_player", table_name="mvp_race_snapshot_candidates")
        op.drop_index("ix_mvp_snapshot_candidates_snapshot_rank", table_name="mvp_race_snapshot_candidates")
        op.drop_table("mvp_race_snapshot_candidates")

    if _has_table("mvp_race_snapshots"):
        op.drop_index("ix_mvp_race_snapshots_season_profile_date", table_name="mvp_race_snapshots")
        op.drop_table("mvp_race_snapshots")
