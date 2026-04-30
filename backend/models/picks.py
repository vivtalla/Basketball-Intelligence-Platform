"""Pydantic schemas for the bracket pick'em surface (Sprint 78 — CF2).

Single-user, localStorage-backed. The backend stores nothing for picks; it
just scores submitted picks against actual playoff outcomes and against the
CourtVue model's predicted bracket.
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Inputs — what the user submits from /picks
# ---------------------------------------------------------------------------


class SeriesPick(BaseModel):
    """One series prediction. Both team picks are abbreviations (e.g. "BOS").

    `games` is the user's predicted series length (4..7); optional because we
    accept partially-filled brackets and only score what's there.
    """
    series_id: str
    winner_team_abbr: str
    games: Optional[int] = Field(default=None, ge=4, le=7)


class AwardPick(BaseModel):
    """One award winner pick. `award` is one of the supported categories."""
    award: Literal["mvp", "coy", "dpoy", "roy"]
    player_id: Optional[int] = None
    player_name: Optional[str] = None


class UserPicks(BaseModel):
    """Complete user submission. All fields optional so the frontend can
    submit progressive updates as the user fills in picks."""
    season: str
    series_picks: List[SeriesPick] = Field(default_factory=list)
    award_picks: List[AwardPick] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------


PickStatus = Literal["correct", "incorrect", "pending", "missing"]


class SeriesPickResult(BaseModel):
    series_id: str
    round: int
    user_winner_abbr: Optional[str] = None
    user_games: Optional[int] = None
    actual_winner_abbr: Optional[str] = None
    actual_games: Optional[int] = None
    model_winner_abbr: Optional[str] = None
    model_games: Optional[int] = None
    winner_status: PickStatus
    games_status: PickStatus
    points: int = 0
    points_possible: int = 0


class AwardPickResult(BaseModel):
    award: str
    user_player_id: Optional[int] = None
    user_player_name: Optional[str] = None
    actual_player_id: Optional[int] = None
    actual_player_name: Optional[str] = None
    model_player_id: Optional[int] = None
    model_player_name: Optional[str] = None
    status: PickStatus
    points: int = 0
    points_possible: int = 0


class HeadToHead(BaseModel):
    """Aggregate user-vs-model comparison across the whole bracket."""
    user_points: int = 0
    model_points: int = 0
    user_correct: int = 0
    model_correct: int = 0
    delta_points: int = 0  # user_points - model_points
    delta_correct: int = 0


class PicksScorecard(BaseModel):
    season: str
    series_results: List[SeriesPickResult] = Field(default_factory=list)
    award_results: List[AwardPickResult] = Field(default_factory=list)
    total_points: int = 0
    total_points_possible: int = 0
    accuracy_pct: float = 0.0
    head_to_head: HeadToHead = Field(default_factory=HeadToHead)


# ---------------------------------------------------------------------------
# CourtVue model — what the simulator predicts
# ---------------------------------------------------------------------------


class ModelSeriesPick(BaseModel):
    series_id: str
    round: int
    winner_team_abbr: Optional[str] = None
    games: Optional[int] = None
    confidence: Optional[float] = None  # 0..1, model's series-win probability


class ModelAwardPick(BaseModel):
    award: str
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    rationale: Optional[str] = None


class ModelPicks(BaseModel):
    season: str
    series_picks: List[ModelSeriesPick] = Field(default_factory=list)
    award_picks: List[ModelAwardPick] = Field(default_factory=list)
