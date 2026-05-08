"""Sprint 93 — composite index gap-fill for hot query patterns.

Sprint 88 added several single-column and partial-composite indexes.
Three patterns remained unindexed:

1. ``season_stats(player_id, season, is_playoff)``
   The UC is ``(player_id, season, team_abbreviation, is_playoff)``.
   Queries that filter by player+season+playoff without team_abbreviation
   can use the UC up to column 2 only; the third column (team_abbreviation)
   breaks prefix use for the is_playoff filter.  A 3-column composite
   closes this gap.

2. ``player_game_logs(player_id, season, game_date)``
   Has a bare player_id index and a (season, season_type) index from
   Sprint 88, but no composite for the common time-series query:
   ``.filter(player_id=X, season=Y).order_by(game_date.desc())``.

3. ``lineup_stats(season, team_id, is_playoff)``
   No column index beyond the UC ``(lineup_key, season, is_playoff)``.
   Opportunity and intelligence services filter by team_id + season +
   is_playoff in a pattern the UC can't serve.

All created with the Sprint 88 guard pattern (_has_table / _has_index).
Reversible (downgrade drops the indexes instantly with no data change).
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "0024_sprint93_perf_idx"
down_revision = "0023_sprint88_perf_indexes"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    names = {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table_name)}
    return index_name in names


INDEXES = [
    (
        "season_stats",
        "ix_season_stats_player_season_playoff",
        ["player_id", "season", "is_playoff"],
    ),
    (
        "player_game_logs",
        "ix_player_game_logs_player_season_date",
        ["player_id", "season", "game_date"],
    ),
    (
        "lineup_stats",
        "ix_lineup_stats_season_team_playoff",
        ["season", "team_id", "is_playoff"],
    ),
]


def upgrade() -> None:
    for table, name, cols in INDEXES:
        if _has_table(table) and not _has_index(table, name):
            op.create_index(name, table, cols)


def downgrade() -> None:
    for table, name, _cols in INDEXES:
        if _has_table(table) and _has_index(table, name):
            op.drop_index(name, table_name=table)
