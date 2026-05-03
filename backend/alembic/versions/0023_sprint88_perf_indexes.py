"""Sprint 88 (B1) — performance indexes on hot query patterns.

Audit found 8 missing indexes across `season_stats`, `player_game_logs`,
`play_by_play_events`, `lineup_stats`, `player_on_off`, `game_player_stats`,
and `game_team_stats`. Several services do `.filter(season=, season_type=)`
+ `.order_by(...)` against these tables (some multi-million-row) without
covering indexes, forcing full scans.

All indexes are CREATE INDEX (no NOT NULL changes; no FK reflection issues).
Reversible. Defensive `_has_table` + `_has_index` guards keep the legacy
SQLite-baseline test path working (Sprint 85 lesson).
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "0023_sprint88_perf_indexes"
down_revision = "0022_sprint86_team_track_hus"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in inspect(op.get_bind()).get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    names = {ix["name"] for ix in inspect(op.get_bind()).get_indexes(table_name)}
    return index_name in names


# (table, index_name, [columns]) — single source of truth for both upgrade + downgrade
INDEXES = [
    ("season_stats", "ix_season_stats_season_isplayoff", ["season", "is_playoff"]),
    ("season_stats", "ix_season_stats_player_season", ["player_id", "season"]),
    ("player_game_logs", "ix_player_game_logs_season_type", ["season", "season_type"]),
    ("play_by_play_events", "ix_play_by_play_events_season", ["season"]),
    ("lineup_stats", "ix_lineup_stats_season_isplayoff_minutes", ["season", "is_playoff", "minutes"]),
    ("player_on_off", "ix_player_on_off_season_isplayoff_net", ["season", "is_playoff", "on_off_net"]),
    ("game_player_stats", "ix_game_player_stats_season", ["season"]),
    ("game_team_stats", "ix_game_team_stats_game_id", ["game_id"]),
]


def upgrade() -> None:
    for table, name, cols in INDEXES:
        # Skip when the table itself isn't present (legacy-baseline test path
        # stamps at 0001 without creating most tables — Sprint 85 lesson).
        if _has_table(table) and not _has_index(table, name):
            op.create_index(name, table, cols)


def downgrade() -> None:
    for table, name, _cols in INDEXES:
        if _has_table(table) and _has_index(table, name):
            op.drop_index(name, table_name=table)
