from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from models.mvp import MvpCandidateCaseResponse, MvpContextMapResponse, MvpRaceResponse
from services.mvp_service import build_mvp_candidate_case, build_mvp_context_map, build_mvp_race

router = APIRouter()


@router.get("/race", response_model=MvpRaceResponse)
def get_mvp_race(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=10, ge=1, le=25, description="Number of candidates to return"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    db: Session = Depends(get_db),
) -> MvpRaceResponse:
    """Return the top-N MVP candidates with case data and pillar scoring."""
    resolved_season = season or _active_nba_season()
    return build_mvp_race(db, season=resolved_season, top=top, min_gp=min_gp, position=position)


@router.get("/candidates/{player_id}/case", response_model=MvpCandidateCaseResponse)
def get_mvp_candidate_case(
    player_id: int,
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    db: Session = Depends(get_db),
) -> MvpCandidateCaseResponse:
    """Return one candidate's full MVP case plus nearby rank context."""
    resolved_season = season or _active_nba_season()
    return build_mvp_candidate_case(db, season=resolved_season, player_id=player_id, min_gp=min_gp, position=position)


@router.get("/context-map", response_model=MvpContextMapResponse)
def get_mvp_context_map(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=20, ge=1, le=50, description="Number of candidates to return"),
    min_gp: int = Query(default=20, ge=1, le=82, description="Minimum games played"),
    position: Optional[str] = Query(default=None, description="Optional position token, e.g. G, F, C"),
    db: Session = Depends(get_db),
) -> MvpContextMapResponse:
    """Return lightweight MVP case-map coordinates and evidence."""
    resolved_season = season or _active_nba_season()
    return build_mvp_context_map(db, season=resolved_season, top=top, min_gp=min_gp, position=position)
