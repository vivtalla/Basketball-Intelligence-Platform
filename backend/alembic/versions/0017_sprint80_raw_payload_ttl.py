"""Sprint 80 — TTL old raw_game_payloads ahead of cloud migration.

Pre-flight cleanup before the ``pg_dump``/``pg_restore`` migration to the
Hetzner-hosted Postgres. Drops ``raw_game_payloads`` rows older than 30 days
to shrink the dump. These payloads are raw NBA API blobs that are stored only
to support re-parsing during ingestion (`_store_raw_game_payload` dedupes
new writes by content hash; nothing reads old rows on a hot path). If we
ever need to re-parse a game older than 30 days, the NBA API can re-serve
the source.

Notes:
- ``play_by_play`` legacy table drop was scoped out (Sprint 81 candidate):
  pre-flight grep found 11+ active readers (possession_diary, pbp_service,
  warehouse_service, game_detail_assembler, shot_lab, pbp_sync, game_trajectory,
  team_intelligence, advanced router, sync_today_playoff_finals, sync_playoff_pbp).
  Dropping it is a multi-sprint refactor of its own.
- VACUUM FULL is intentionally not invoked here — Alembic migrations run inside
  a transaction and ``VACUUM FULL`` cannot. Run it manually post-migration:
  ``psql bip -c 'VACUUM FULL raw_game_payloads;'``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision = "0017_sprint80_raw_payload_ttl"
down_revision = "0016_sprint79_award_voting"
branch_labels = None
depends_on = None


def _has_table(table_name):
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def upgrade():
    if not _has_table("raw_game_payloads"):
        return

    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        cutoff = "NOW() - INTERVAL '30 days'"
    elif dialect == "sqlite":
        cutoff = "datetime('now', '-30 days')"
    else:
        cutoff = "CURRENT_TIMESTAMP"

    op.execute(sa.text(
        "DELETE FROM raw_game_payloads "
        "WHERE fetched_at IS NOT NULL AND fetched_at < {0}".format(cutoff)
    ))


def downgrade():
    # Irreversible — old payloads are unrecoverable. Re-fetch from the
    # NBA API via bulk_import / sync_playoff_pbp if needed.
    pass
