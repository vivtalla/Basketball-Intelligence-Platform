"""Sprint 85 — bracket auto-advancement.

Adds two nullable parent-pointer columns to ``playoff_series`` so when a
Round-N series closes 4-X, we can stand up a Round-(N+1) row pre-populated
with the winner and a TBD opponent until the parallel arm closes.

Both columns are nullable because Round 1 series have no parents. They are
indexed so reverse lookups ("which child slot already has me as a parent?")
are cheap during ``build_or_refresh_bracket`` re-runs.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0021_sprint85_bracket_advance"
down_revision = "0020_sprint81_pl_splits_pt"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    cols = {col["name"] for col in inspect(op.get_bind()).get_columns(table_name)}
    return column_name in cols


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    names = {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table_name)}
    return index_name in names


def upgrade() -> None:
    if not _has_table("playoff_series"):
        # Defensive — Sprint 73 created the table; nothing to do otherwise.
        return

    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if not _has_column("playoff_series", "parent_top_series_id"):
        op.add_column(
            "playoff_series",
            sa.Column("parent_top_series_id", sa.String(80), nullable=True),
        )
    if not _has_column("playoff_series", "parent_bottom_series_id"):
        op.add_column(
            "playoff_series",
            sa.Column("parent_bottom_series_id", sa.String(80), nullable=True),
        )

    if not _has_index("playoff_series", "ix_playoff_series_parent_top"):
        op.create_index(
            "ix_playoff_series_parent_top",
            "playoff_series",
            ["parent_top_series_id"],
        )
    if not _has_index("playoff_series", "ix_playoff_series_parent_bottom"):
        op.create_index(
            "ix_playoff_series_parent_bottom",
            "playoff_series",
            ["parent_bottom_series_id"],
        )

    # Round-(N+1) auto-advance rows are stood up the moment one parent closes,
    # which means the other parent's seed/team_id is still unknown. Relax the
    # NOT NULL constraints on top/bottom seed pointers so we can persist that
    # half-populated state until the parallel arm finishes.
    if dialect_name == "sqlite":
        with op.batch_alter_table("playoff_series") as batch_op:
            batch_op.alter_column("top_seed_team_id", existing_type=sa.Integer(), nullable=True)
            batch_op.alter_column("bottom_seed_team_id", existing_type=sa.Integer(), nullable=True)
            batch_op.alter_column("top_seed", existing_type=sa.Integer(), nullable=True)
            batch_op.alter_column("bottom_seed", existing_type=sa.Integer(), nullable=True)
    else:
        op.alter_column("playoff_series", "top_seed_team_id", existing_type=sa.Integer(), nullable=True)
        op.alter_column("playoff_series", "bottom_seed_team_id", existing_type=sa.Integer(), nullable=True)
        op.alter_column("playoff_series", "top_seed", existing_type=sa.Integer(), nullable=True)
        op.alter_column("playoff_series", "bottom_seed", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    if not _has_table("playoff_series"):
        return

    bind = op.get_bind()
    dialect_name = bind.dialect.name

    # Restore the NOT NULL constraints on seed pointers. Any auto-advance rows
    # with NULL pointers are deleted first; downgrade is destructive but the
    # data is regenerable from `game_logs` via build_or_refresh_bracket.
    op.execute(
        "DELETE FROM playoff_series "
        "WHERE top_seed_team_id IS NULL OR bottom_seed_team_id IS NULL "
        "OR top_seed IS NULL OR bottom_seed IS NULL"
    )

    if dialect_name == "sqlite":
        with op.batch_alter_table("playoff_series") as batch_op:
            batch_op.alter_column("top_seed_team_id", existing_type=sa.Integer(), nullable=False)
            batch_op.alter_column("bottom_seed_team_id", existing_type=sa.Integer(), nullable=False)
            batch_op.alter_column("top_seed", existing_type=sa.Integer(), nullable=False)
            batch_op.alter_column("bottom_seed", existing_type=sa.Integer(), nullable=False)
    else:
        op.alter_column("playoff_series", "top_seed_team_id", existing_type=sa.Integer(), nullable=False)
        op.alter_column("playoff_series", "bottom_seed_team_id", existing_type=sa.Integer(), nullable=False)
        op.alter_column("playoff_series", "top_seed", existing_type=sa.Integer(), nullable=False)
        op.alter_column("playoff_series", "bottom_seed", existing_type=sa.Integer(), nullable=False)

    if _has_index("playoff_series", "ix_playoff_series_parent_bottom"):
        op.drop_index(
            "ix_playoff_series_parent_bottom",
            table_name="playoff_series",
        )
    if _has_index("playoff_series", "ix_playoff_series_parent_top"):
        op.drop_index(
            "ix_playoff_series_parent_top",
            table_name="playoff_series",
        )

    if _has_column("playoff_series", "parent_bottom_series_id"):
        op.drop_column("playoff_series", "parent_bottom_series_id")
    if _has_column("playoff_series", "parent_top_series_id"):
        op.drop_column("playoff_series", "parent_top_series_id")
