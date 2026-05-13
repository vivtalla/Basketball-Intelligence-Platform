"""Sprint 98 Stream B1 — FK constraints on PlayoffSeries parent pointers.

``PlayoffSeries.parent_top_series_id`` and ``parent_bottom_series_id`` were
introduced in Sprint 85 as raw ``String(80)`` columns referencing
``playoff_series.series_id``, but the reference was not enforced — bad
values could (and did, per Sprint 97's stale R2 placeholder rows) sit
in the table indefinitely.

This migration:
  1. Defensively nulls any orphan parent_*_series_id values that don't
     match an existing series_id. Expected count: 0 after Sprint 97's
     cleanup, but checked so the migration is safe to rerun.
  2. Adds a unique index on ``series_id`` (since the existing UC is
     composite on (season, series_id), the column isn't uniquely
     indexed and can't be an FK target on its own). Verified before
     the index is added that no duplicates exist; if any do, the
     migration logs them and aborts so a human can decide.
  3. Adds ForeignKey constraints with ``ON DELETE SET NULL`` so deleting
     a parent series doesn't cascade-destroy bracket structure — the
     downstream slot just loses its parent pointer and waits for
     manual repair.

Sprint 88+ guard pattern with ``_has_table`` / ``_has_constraint`` /
``_has_index`` so the migration is idempotent on partial-apply.
"""
from __future__ import annotations

import logging

from alembic import op
from sqlalchemy import inspect, text


revision = "0025_sprint98_fk_pp"
down_revision = "0024_sprint93_perf_idx"
branch_labels = None
depends_on = None


logger = logging.getLogger("alembic.0025")

TABLE = "playoff_series"
UNIQUE_INDEX = "ix_playoff_series_series_id_unique"
FK_TOP = "fk_playoff_series_parent_top"
FK_BOTTOM = "fk_playoff_series_parent_bottom"


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return index_name in {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table_name)}


def _has_fk(table_name: str, fk_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return fk_name in {fk.get("name") for fk in inspect(op.get_bind()).get_foreign_keys(table_name)}


def upgrade() -> None:
    if not _has_table(TABLE):
        return

    bind = op.get_bind()

    # 1. Null any orphan parent pointers. With Postgres-style placeholders
    # this works for both SQLite and Postgres. Counts logged so the value
    # surfaces in alembic output.
    orphan_top = bind.execute(
        text(
            "UPDATE playoff_series "
            "SET parent_top_series_id = NULL "
            "WHERE parent_top_series_id IS NOT NULL "
            "AND parent_top_series_id NOT IN (SELECT series_id FROM playoff_series)"
        )
    ).rowcount or 0
    orphan_bottom = bind.execute(
        text(
            "UPDATE playoff_series "
            "SET parent_bottom_series_id = NULL "
            "WHERE parent_bottom_series_id IS NOT NULL "
            "AND parent_bottom_series_id NOT IN (SELECT series_id FROM playoff_series)"
        )
    ).rowcount or 0
    if orphan_top or orphan_bottom:
        logger.warning(
            "0025 nulled orphans: top=%d, bottom=%d", orphan_top, orphan_bottom,
        )

    # 2. Refuse to proceed if series_id has duplicates — the FK target
    # must be unique. Defensive: format encodes season so duplicates are
    # not expected in production data.
    dup_rows = bind.execute(
        text(
            "SELECT series_id, COUNT(*) AS n FROM playoff_series "
            "GROUP BY series_id HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dup_rows:
        raise RuntimeError(
            "0025: cannot add unique index on playoff_series.series_id — "
            f"{len(dup_rows)} duplicate series_id rows found: {[r[0] for r in dup_rows[:10]]}. "
            "Resolve duplicates before re-running this migration."
        )

    # 3. Unique index on series_id so the parent_*_series_id FKs have a
    # valid target. The composite UC (season, series_id) stays in place
    # for legacy callers; this is additive.
    if not _has_index(TABLE, UNIQUE_INDEX):
        op.create_index(UNIQUE_INDEX, TABLE, ["series_id"], unique=True)

    # 4. FKs with ON DELETE SET NULL on both parent pointers. SQLite
    # doesn't enforce FKs unless PRAGMA foreign_keys=ON is set per
    # connection, so this is mostly a Postgres-side guarantee.
    dialect = bind.dialect.name
    if dialect != "sqlite":
        if not _has_fk(TABLE, FK_TOP):
            op.create_foreign_key(
                FK_TOP,
                TABLE,
                TABLE,
                ["parent_top_series_id"],
                ["series_id"],
                ondelete="SET NULL",
            )
        if not _has_fk(TABLE, FK_BOTTOM):
            op.create_foreign_key(
                FK_BOTTOM,
                TABLE,
                TABLE,
                ["parent_bottom_series_id"],
                ["series_id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    if not _has_table(TABLE):
        return
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        if _has_fk(TABLE, FK_BOTTOM):
            op.drop_constraint(FK_BOTTOM, TABLE, type_="foreignkey")
        if _has_fk(TABLE, FK_TOP):
            op.drop_constraint(FK_TOP, TABLE, type_="foreignkey")
    if _has_index(TABLE, UNIQUE_INDEX):
        op.drop_index(UNIQUE_INDEX, table_name=TABLE)
