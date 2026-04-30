"""Bracket Pick'em router (Sprint 78 — CF2).

Routes:

- ``POST /api/picks/score`` — body: UserPicks, returns a PicksScorecard with
  per-series correctness, points, and head-to-head delta vs the CourtVue
  model.
- ``GET /api/picks/model?season=YYYY-YY`` — returns the CourtVue model's
  bracket + award picks so the frontend can render "model's pick" alongside
  the user's selection.

Picks themselves are localStorage-backed on the frontend; the backend never
persists user picks.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.picks import ModelPicks, PicksScorecard, UserPicks
from services.picks_scoring_service import get_model_picks, score_user_picks

router = APIRouter()


@router.post("/score", response_model=PicksScorecard)
def post_score(
    user_picks: UserPicks,
    db: Session = Depends(get_db),
) -> PicksScorecard:
    """Score the submitted picks against actuals + the CourtVue model bracket."""
    return score_user_picks(db, user_picks)


@router.get("/model", response_model=ModelPicks)
def get_model(
    season: str = Query(..., description="Season string, e.g. '2025-26'."),
    db: Session = Depends(get_db),
) -> ModelPicks:
    """Return the CourtVue model's predicted bracket + award picks."""
    return get_model_picks(db, season)
