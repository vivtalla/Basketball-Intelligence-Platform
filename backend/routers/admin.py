"""Sprint 98 — Admin / diagnostic endpoints.

All routes here require the ``X-Admin-Key`` header (Sprint 93 dependency)
and are not exposed in the user-facing nav. They surface internal state
useful for operators investigating data drift, sync gaps, or other
production anomalies.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from dependencies import require_admin_key
from services.playoff_drift_detector import detect_drift


router = APIRouter(dependencies=[Depends(require_admin_key)])


@router.get("/playoff-series-drift")
def playoff_series_drift(
    season: Optional[str] = Query(None, description="Optional season filter (e.g. 2025-26)"),
    db: Session = Depends(get_db),
):
    """Return PlayoffSeries rows whose denormalized win counts disagree
    with the ``playoff_series_win_truth`` view.

    Empty ``drift`` list means the cache is consistent. Non-empty means
    Sprint 97's class of issue happened again — a game was inserted
    without the bracket builder being run, or top_wins/bottom_wins was
    written by a path other than ``build_or_refresh_bracket``.
    """
    drift = detect_drift(db, season=season)
    return {"count": len(drift), "drift": drift, "season": season}
