"""Sprint 98 Stream B4 — playoff_series_win_truth view.

Sprint 97 closeout flagged ``PlayoffSeries.top_wins`` / ``bottom_wins`` as a
denormalized cache that's the source of every win-count drift we've
patched around. Sprint 98 is surgical (per Vivek's Q3 answer): we
intentionally do NOT replace the columns. Instead we add a SQL view
that computes the wins truth from ``game_logs`` at query time, plus an
admin-key-gated diagnostic endpoint that returns drift rows.

The view is the canonical source for future cleanup; right now it just
powers ``/api/admin/playoff-series-drift``. When Sprint 99+ replaces the
denormalized columns, callers migrate to the view one by one.

The view depends on:
  - ``playoff_series.series_id``
  - ``game_logs.series_id``, ``game_logs.home_team_id``,
    ``game_logs.away_team_id``, ``game_logs.home_score``,
    ``game_logs.away_score``, ``game_logs.season_type``
  - ``playoff_series.top_seed_team_id``, ``bottom_seed_team_id``

A game counts as a top-seed win when (home_team_id = top_seed AND
home_score > away_score) OR (away_team_id = top_seed AND
away_score > home_score). Symmetric for bottom seed. Games with NULL
seed pointers or missing scores are ignored.

SQLite (used in tests) supports CREATE VIEW; Postgres does too with
identical syntax for this query shape. Reversible via DROP VIEW.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect


revision = "0027_sprint98_view"
down_revision = "0026_sprint98_audit_cols"
branch_labels = None
depends_on = None


VIEW = "playoff_series_win_truth"

VIEW_SQL = f"""
CREATE VIEW {VIEW} AS
SELECT
    ps.series_id AS series_id,
    ps.season AS season,
    ps.top_seed_team_id AS top_seed_team_id,
    ps.bottom_seed_team_id AS bottom_seed_team_id,
    COALESCE(SUM(
        CASE
            WHEN ps.top_seed_team_id IS NOT NULL
                 AND gl.home_score IS NOT NULL
                 AND gl.away_score IS NOT NULL
                 AND (
                     (gl.home_team_id = ps.top_seed_team_id AND gl.home_score > gl.away_score)
                     OR (gl.away_team_id = ps.top_seed_team_id AND gl.away_score > gl.home_score)
                 )
            THEN 1 ELSE 0
        END
    ), 0) AS top_wins,
    COALESCE(SUM(
        CASE
            WHEN ps.bottom_seed_team_id IS NOT NULL
                 AND gl.home_score IS NOT NULL
                 AND gl.away_score IS NOT NULL
                 AND (
                     (gl.home_team_id = ps.bottom_seed_team_id AND gl.home_score > gl.away_score)
                     OR (gl.away_team_id = ps.bottom_seed_team_id AND gl.away_score > gl.home_score)
                 )
            THEN 1 ELSE 0
        END
    ), 0) AS bottom_wins,
    COUNT(gl.game_id) AS games_played
FROM playoff_series ps
LEFT JOIN game_logs gl
    ON gl.series_id = ps.series_id
    AND gl.season_type = 'Playoffs'
GROUP BY ps.series_id, ps.season, ps.top_seed_team_id, ps.bottom_seed_team_id
""".strip()


def _has_view(view_name: str) -> bool:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        row = bind.exec_driver_sql(
            f"SELECT name FROM sqlite_master WHERE type = 'view' AND name = '{view_name}'"
        ).first()
        return row is not None
    # Postgres
    row = bind.exec_driver_sql(
        "SELECT 1 FROM information_schema.views "
        "WHERE table_schema = ANY(current_schemas(false)) AND table_name = %s",
        (view_name,),
    ).first()
    return row is not None


def upgrade() -> None:
    if not inspect(op.get_bind()).has_table("playoff_series"):
        return
    if not inspect(op.get_bind()).has_table("game_logs"):
        return
    if _has_view(VIEW):
        op.execute(f"DROP VIEW {VIEW}")
    op.execute(VIEW_SQL)


def downgrade() -> None:
    if _has_view(VIEW):
        op.execute(f"DROP VIEW {VIEW}")
