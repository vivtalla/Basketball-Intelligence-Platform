"""Sprint 98 Stream B4 — Playoff series drift detector.

``PlayoffSeries.top_wins`` and ``bottom_wins`` are denormalized cache
columns; they get out of sync with reality whenever a game is inserted
without the bracket builder running (Sprint 97 incident class). Sprint
98 keeps the columns in place (surgical scope) but adds the
``playoff_series_win_truth`` view (migration 0027) as the canonical
source plus this detector that compares the two and returns the diff.

The diagnostic endpoint ``/api/admin/playoff-series-drift`` reads this
service. Empty result = healthy steady state.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from db.models import PlayoffSeries


def detect_drift(db: Session, *, season: Optional[str] = None) -> List[Dict]:
    """Return rows where the denormalized win counts disagree with the
    view's computed truth.

    Args:
        db: SQLAlchemy session.
        season: optional filter (e.g. ``"2025-26"``). When None, every
            season's series is checked.

    Returns:
        List of drift records, each containing ``series_id``, ``season``,
        ``cached_top_wins``, ``true_top_wins``, ``cached_bottom_wins``,
        ``true_bottom_wins``, ``games_played``. Empty list = no drift.
    """
    base = (
        "SELECT ps.series_id AS series_id, "
        "ps.season AS season, "
        "ps.top_wins AS cached_top_wins, "
        "view.top_wins AS true_top_wins, "
        "ps.bottom_wins AS cached_bottom_wins, "
        "view.bottom_wins AS true_bottom_wins, "
        "view.games_played AS games_played "
        "FROM playoff_series ps "
        "JOIN playoff_series_win_truth view ON view.series_id = ps.series_id "
        "WHERE (ps.top_wins != view.top_wins OR ps.bottom_wins != view.bottom_wins)"
    )
    params: Dict[str, str] = {}
    if season:
        base += " AND ps.season = :season"
        params["season"] = season
    base += " ORDER BY ps.season, ps.series_id"

    rows = db.execute(text(base), params).fetchall()
    return [
        {
            "series_id": row[0],
            "season": row[1],
            "cached_top_wins": int(row[2] or 0),
            "true_top_wins": int(row[3] or 0),
            "cached_bottom_wins": int(row[4] or 0),
            "true_bottom_wins": int(row[5] or 0),
            "games_played": int(row[6] or 0),
        }
        for row in rows
    ]


__all__ = ["detect_drift"]
