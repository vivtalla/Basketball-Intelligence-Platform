from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from models.mvp import MvpRaceResponse
from services.mvp_service import build_mvp_race

router = APIRouter()


@router.get("/race", response_model=MvpRaceResponse)
def get_mvp_race(
    season: str = Query(default=None, description="Season string, e.g. 2024-25"),
    top: int = Query(default=10, ge=1, le=25, description="Number of candidates to return"),
    db: Session = Depends(get_db),
) -> MvpRaceResponse:
    """Return the top-N MVP candidates for the given season, ranked by
    composite z-score across PTS, REB, AST, TS%, and BPM.

    Augments each candidate with a last-10-game momentum signal.
    """
    resolved_season = season or _active_nba_season()
    return build_mvp_race(db, season=resolved_season, top=top)
