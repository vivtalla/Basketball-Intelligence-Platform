"""Sprint 81 — award_case_candidates table for mvp_case_v5 calibration.

Holds historical Basketball Value + 5-pillar modifier vectors per (player,
season). Without this materialization the LOO-CV harness can't fit
calibrated weights, so ``mvp_case_v5`` was shipping with
``calibration_pending=True`` since Sprint 79.

Sprint 81 lands the table; ``data/materialize_award_modifiers.py`` writes
rows into it for every season referenced by ``award_voting``.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0019_sprint81_award_cands"
down_revision = "0018_sprint81_drop_legacy_pbp"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if _has_table("award_case_candidates"):
        return

    op.create_table(
        "award_case_candidates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("player_id", sa.Integer, sa.ForeignKey("players.id"), nullable=False),
        sa.Column("season", sa.String(10), nullable=False),
        sa.Column("award_type", sa.String(10), nullable=False, server_default="MVP"),
        sa.Column("basketball_value", sa.Float, nullable=False),
        sa.Column("modifier_team_framing", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("modifier_eligibility_pressure", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("modifier_clutch", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("modifier_momentum", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("modifier_signature_games", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("last_synced_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("player_id", "season", "award_type", name="uq_award_case_candidate"),
    )
    op.create_index(
        "ix_award_case_candidates_season",
        "award_case_candidates",
        ["season"],
    )


def downgrade() -> None:
    if _has_table("award_case_candidates"):
        op.drop_index("ix_award_case_candidates_season", table_name="award_case_candidates")
        op.drop_table("award_case_candidates")
