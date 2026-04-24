"""Sprint 66 — pre-read packet metadata.

Revision ID: 0010_pre_read_packet_metadata
Revises: 0009_team_shooting_split_stats
Create Date: 2026-04-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_pre_read_packet_metadata"
down_revision = "0009_team_shooting_split_stats"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "pre_read_snapshots" not in inspector.get_table_names():
        return
    if not _has_column("pre_read_snapshots", "title"):
        op.add_column("pre_read_snapshots", sa.Column("title", sa.String(length=160), nullable=True))
    if not _has_column("pre_read_snapshots", "note"):
        op.add_column("pre_read_snapshots", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "pre_read_snapshots" not in inspector.get_table_names():
        return
    if _has_column("pre_read_snapshots", "note"):
        op.drop_column("pre_read_snapshots", "note")
    if _has_column("pre_read_snapshots", "title"):
        op.drop_column("pre_read_snapshots", "title")
