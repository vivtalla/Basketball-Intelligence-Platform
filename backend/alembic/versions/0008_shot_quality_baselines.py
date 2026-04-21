"""Sprint 61 — shot_quality_baselines materialization table.

Persist per-(season, season_type, methodology_version) expected-shot baselines
so /shotchart/{player_id}/quality does not recompute league-wide baselines on
every request.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0008_shot_quality_baselines"
down_revision = "0007_mvp_race_timeline"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("shot_quality_baselines"):
        op.create_table(
            "shot_quality_baselines",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("season", sa.String(length=10), nullable=False),
            sa.Column(
                "season_type",
                sa.String(length=30),
                nullable=False,
                server_default="Regular Season",
            ),
            sa.Column(
                "methodology_version",
                sa.String(length=40),
                nullable=False,
                server_default="shot_quality_v1",
            ),
            sa.Column("sample_n", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column(
                "computed_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=True,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "season",
                "season_type",
                "methodology_version",
                name="uq_shot_quality_baseline_key",
            ),
        )
        op.create_index(
            "ix_shot_quality_baselines_lookup",
            "shot_quality_baselines",
            ["season", "season_type", "methodology_version"],
        )


def downgrade() -> None:
    if _has_table("shot_quality_baselines"):
        op.drop_index(
            "ix_shot_quality_baselines_lookup",
            table_name="shot_quality_baselines",
        )
        op.drop_table("shot_quality_baselines")
