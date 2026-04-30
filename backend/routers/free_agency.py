"""Sprint 78 — FO2 Free Agency Workspace endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from models.free_agency import FreeAgencyResponse, FreeAgentFitsResponse
from services.free_agency_service import (
    compute_expiring_contracts,
    top_team_fits_for_player,
)

router = APIRouter()


@router.get("", response_model=FreeAgencyResponse)
def list_free_agents(
    season: Optional[str] = Query(default=None, description="Season string, e.g. 2025-26"),
    tier: Optional[str] = Query(default=None, description="Filter: max | above_mid | mid_level | minimum | two_way"),
    position: Optional[str] = Query(default=None, description="Filter: position substring (e.g. 'guard', 'sf')"),
    age_max: Optional[int] = Query(default=None, ge=18, le=50, description="Filter: maximum age"),
    db: Session = Depends(get_db),
) -> FreeAgencyResponse:
    """League-wide expiring-contract leaderboard with tier/position/age filters.

    Returns an empty workspace (`is_empty_dataset=True`) when
    `player_contracts` has not been ingested yet.
    """
    resolved_season = season or _active_nba_season()
    return compute_expiring_contracts(
        db,
        season=resolved_season,
        tier=tier,
        position=position,
        age_max=age_max,
    )


@router.get("/{player_id}/fits", response_model=FreeAgentFitsResponse)
def get_free_agent_fits(
    player_id: int,
    season: Optional[str] = Query(default=None, description="Season string, e.g. 2025-26"),
    k: int = Query(default=10, ge=1, le=10, description="Number of top fits to return (max 10)"),
    db: Session = Depends(get_db),
) -> FreeAgentFitsResponse:
    """Top-K team-fit rankings for a single free agent with rationale chips."""
    resolved_season = season or _active_nba_season()
    return top_team_fits_for_player(db, player_id, season=resolved_season, k=k)
