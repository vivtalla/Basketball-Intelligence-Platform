"""Sprint 98 Stream B2 — audit columns on AwardCaseCandidate + RoleExpansionObservation.

Both tables were added without the standard ``created_at`` + ``updated_at``
pair that older tables carry:

  - ``AwardCaseCandidate`` (Sprint 81) has only ``last_synced_at``.
  - ``RoleExpansionObservation`` (Sprint 79) has only ``computed_at``.

Sprint 98 audit flagged this as a precedent risk — new models adopting the
shape lose the ability to distinguish insertion from last update, which
matters for cohort backfills and the freshness markers introduced in
Stream A. Backfills set the new columns to whatever timestamp the
existing audit column held, so no historical data is invented.

Sprint 88+ guard pattern (``_has_table`` / ``_has_column``) keeps the
migration idempotent.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


revision = "0026_sprint98_audit_cols"
down_revision = "0025_sprint98_fk_pp"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return column_name in {col["name"] for col in inspect(op.get_bind()).get_columns(table_name)}


def _add_audit_cols(table_name: str, source_column: str) -> None:
    """Add ``created_at`` + ``updated_at`` to a table, backfilled from
    ``source_column`` (an existing audit-ish column on the table).
    """
    if not _has_table(table_name):
        return

    if not _has_column(table_name, "created_at"):
        op.add_column(
            table_name,
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )
        if _has_column(table_name, source_column):
            op.execute(
                f"UPDATE {table_name} "
                f"SET created_at = {source_column} "
                f"WHERE created_at IS NULL AND {source_column} IS NOT NULL"
            )

    if not _has_column(table_name, "updated_at"):
        op.add_column(
            table_name,
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=True,
            ),
        )
        if _has_column(table_name, source_column):
            op.execute(
                f"UPDATE {table_name} "
                f"SET updated_at = {source_column} "
                f"WHERE updated_at IS NULL AND {source_column} IS NOT NULL"
            )


def upgrade() -> None:
    _add_audit_cols("award_case_candidates", source_column="last_synced_at")
    _add_audit_cols("role_expansion_observations", source_column="computed_at")


def downgrade() -> None:
    for table in ("role_expansion_observations", "award_case_candidates"):
        if not _has_table(table):
            continue
        for col in ("updated_at", "created_at"):
            if _has_column(table, col):
                op.drop_column(table, col)
