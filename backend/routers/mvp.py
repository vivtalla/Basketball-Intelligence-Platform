from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from models.mvp import (
    MvpCandidateCaseResponse,
    MvpContextMapResponse,
    MvpGravityLeaderboardResponse,
    MvpRaceResponse,
    MvpSensitivityResponse,
    MvpTimelineResponse,
)
from services.mvp_service import (
    AVAILABLE_PROFILES,
    build_mvp_candidate_case,
    build_mvp_context_map,
    build_mvp_gravity_leaderboard,
    build_mvp_race,
    build_mvp_sensitivity,
)
from services.mvp_timeline_service import build_mvp_timeline

router = APIRouter()

_PROFILE_DESCRIPTION = (
    "Scoring profile: one of box_first, balanced, impact_consensus. Default: balanced."
)


@router.get("/race", response_model=MvpRaceResponse)
def get_mvp_race(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=10, ge=1, le=25, description="Number of candidates to return"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    db: Session = Depends(get_db),
) -> MvpRaceResponse:
    """Return the top-N MVP candidates with case data and pillar scoring."""
    resolved_season = season or _active_nba_season()
    return build_mvp_race(
        db, season=resolved_season, top=top, min_gp=min_gp, position=position, profile=profile
    )


@router.get("/gravity", response_model=MvpGravityLeaderboardResponse)
def get_mvp_gravity(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=20, ge=1, le=50, description="Number of gravity profiles to return"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    db: Session = Depends(get_db),
) -> MvpGravityLeaderboardResponse:
    """Return lightweight MVP Gravity leaderboard context."""
    resolved_season = season or _active_nba_season()
    return build_mvp_gravity_leaderboard(db, season=resolved_season, top=top, min_gp=min_gp, position=position)


@router.get("/candidates/{player_id}/case", response_model=MvpCandidateCaseResponse)
def get_mvp_candidate_case(
    player_id: int,
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    db: Session = Depends(get_db),
) -> MvpCandidateCaseResponse:
    """Return one candidate's full MVP case plus nearby rank context."""
    resolved_season = season or _active_nba_season()
    return build_mvp_candidate_case(
        db,
        season=resolved_season,
        player_id=player_id,
        min_gp=min_gp,
        position=position,
        profile=profile,
    )


@router.get("/context-map", response_model=MvpContextMapResponse)
def get_mvp_context_map(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=20, ge=1, le=50, description="Number of candidates to return"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    db: Session = Depends(get_db),
) -> MvpContextMapResponse:
    """Return lightweight MVP case-map coordinates and evidence."""
    resolved_season = season or _active_nba_season()
    return build_mvp_context_map(
        db, season=resolved_season, top=top, min_gp=min_gp, position=position, profile=profile
    )


@router.get("/sensitivity", response_model=MvpSensitivityResponse)
def get_mvp_sensitivity(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=15, ge=1, le=30, description="Number of candidates to include"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    db: Session = Depends(get_db),
) -> MvpSensitivityResponse:
    """Return rank-by-profile for the top-N candidates — used by the ranking-shift slope chart."""
    resolved_season = season or _active_nba_season()
    return build_mvp_sensitivity(
        db, season=resolved_season, top=top, min_gp=min_gp, position=position
    )


@router.get("/timeline", response_model=MvpTimelineResponse)
def get_mvp_timeline(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    profile: Optional[str] = Query(default=None, description=_PROFILE_DESCRIPTION),
    days: int = Query(default=210, ge=2, le=240, description="Number of recent timeline days to include"),
    top: int = Query(default=8, ge=1, le=15, description="Number of latest candidates to include"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    db: Session = Depends(get_db),
) -> MvpTimelineResponse:
    """Return persisted MVP race movement across daily snapshots."""
    resolved_season = season or _active_nba_season()
    return build_mvp_timeline(
        db,
        season=resolved_season,
        profile=profile or "balanced",
        days=days,
        top=top,
        min_gp=min_gp,
    )


@router.get("/profiles")
def get_mvp_profiles() -> dict:
    """Return the list of available scoring profile names (stable for UI pill groups)."""
    return {"profiles": AVAILABLE_PROFILES, "default": "balanced"}
