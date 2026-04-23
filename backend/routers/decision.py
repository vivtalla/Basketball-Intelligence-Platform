from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.decision import (
    FollowThroughRequest,
    FollowThroughResponse,
    H2HResponse,
    LineupImpactResponse,
    MatchupFlagsResponse,
    OpponentPlayTypeResponse,
    PaceEdge,
    PlayTypeEVResponse,
)
from services.decision_support_service import (
    build_follow_through_report,
    build_lineup_impact_report,
    build_matchup_flags_report,
    build_pace_edge,
    build_play_type_ev_report,
)
from services.h2h_service import build_h2h_history
from services.opponent_play_type_service import build_opponent_play_type_report

router = APIRouter()
follow_router = APIRouter()


@router.get("/lineup-impact", response_model=LineupImpactResponse)
def get_lineup_impact(
    team: str = Query(...),
    season: str = Query("2025-26"),
    opponent: Optional[str] = Query(None),
    window: int = Query(10, ge=1, le=30),
    min_possessions: int = Query(25, ge=1),
    db: Session = Depends(get_db),
):
    return build_lineup_impact_report(
        db=db,
        team_abbr=team,
        season=season,
        opponent_abbr=opponent,
        window_games=window,
        min_possessions=min_possessions,
    )


@router.get("/play-type-ev", response_model=PlayTypeEVResponse)
def get_play_type_ev(
    team: str = Query(...),
    season: str = Query("2025-26"),
    opponent: Optional[str] = Query(None),
    window: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
):
    return build_play_type_ev_report(
        db=db,
        team_abbr=team,
        season=season,
        opponent_abbr=opponent,
        window_games=window,
    )


@router.get("/matchup-flags", response_model=MatchupFlagsResponse)
def get_matchup_flags(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2025-26"),
    db: Session = Depends(get_db),
):
    return build_matchup_flags_report(
        db=db,
        team_abbr=team,
        opponent_abbr=opponent,
        season=season,
    )


@follow_router.post("/games", response_model=FollowThroughResponse)
def follow_through_games(
    payload: FollowThroughRequest,
    db: Session = Depends(get_db),
):
    return build_follow_through_report(db=db, payload=payload)


@router.get("/opponent-play-types", response_model=OpponentPlayTypeResponse)
def get_opponent_play_types(
    team: str = Query(...),
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    return build_opponent_play_type_report(db=db, team_abbr=team, season=season)


@router.get("/h2h", response_model=H2HResponse)
def get_h2h_history(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    return build_h2h_history(db=db, team_abbr=team, opponent_abbr=opponent, season=season)


@router.get("/pace-edge", response_model=PaceEdge)
def get_pace_edge(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    return build_pace_edge(db=db, team_abbr=team, opponent_abbr=opponent, season=season)
