"""Sprint 78 CF5 — Streaks & milestones API surface.

Three read-only endpoints, all driven by nightly-recomputed snapshot tables:

- ``GET /api/milestones/active-streaks`` — top-N longest active streaks
- ``GET /api/milestones/approaching``     — closest career milestones
- ``GET /api/milestones/signature-performances`` — last-game signature lines

Routes do not trigger recomputation — they read pre-computed snapshots.
The nightly ``data/sync_streaks_milestones.py`` CLI (wired into
``daily_sync.sh``) refreshes the underlying tables.
"""
from __future__ import annotations

import logging
from datetime import date as _date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.milestones import (
    ActiveStreaksResponse,
    ApproachingMilestonesResponse,
    MilestoneSnapshotSummary,
    PlayerStreakSummary,
    SignaturePerformance,
    SignaturePerformancesResponse,
)
from services.milestone_proximity_service import fetch_approaching_milestones
from services.signature_performance_service import compute_signature_performances
from services.streak_detection_service import fetch_top_active_streaks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/active-streaks", response_model=ActiveStreaksResponse)
def get_active_streaks(
    season: Optional[str] = Query(
        None, description="Season filter, e.g. '2025-26'. Defaults to all seasons."
    ),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ActiveStreaksResponse:
    """Return the top-N longest active player streaks across the league."""
    rows = fetch_top_active_streaks(db, season=season, limit=limit)
    streaks = [PlayerStreakSummary(**row) for row in rows]
    return ActiveStreaksResponse(season=season or "", streaks=streaks)


@router.get("/approaching", response_model=ApproachingMilestonesResponse)
def get_approaching_milestones(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApproachingMilestonesResponse:
    """Return the closest approaching career milestones across the league."""
    rows = fetch_approaching_milestones(db, limit=limit)
    milestones = [MilestoneSnapshotSummary(**row) for row in rows]
    return ApproachingMilestonesResponse(milestones=milestones)


@router.get("/signature-performances", response_model=SignaturePerformancesResponse)
def get_signature_performances(
    date: Optional[str] = Query(
        None, description="ISO 8601 date (YYYY-MM-DD). Defaults to last completed game date."
    ),
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db),
) -> SignaturePerformancesResponse:
    """Return signature box-score lines from a date's slate.

    Each entry ranks the player's box score against their full career
    distribution; only games in the top 10% of a player's career are
    returned, tiered into "career" (top 5%) and "signature" (top 10%).
    """
    target_date: Optional[_date] = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            target_date = None  # fall back to last completed date

    rows = compute_signature_performances(db, target_date=target_date, limit=limit)
    performances = [SignaturePerformance(**row) for row in rows]

    # Surface the actual date used so the client can label the panel
    # ("Tonight's signature performances · Apr 27") even when the request
    # didn't pass an explicit date.
    used_date: Optional[_date] = target_date
    if used_date is None and performances:
        used_date = performances[0].game_date

    return SignaturePerformancesResponse(date=used_date, performances=performances)
