"""Pydantic schemas for the Sprint 78 CF5 Streaks & Milestones tracker.

Three response payloads, one entry schema each:

- ``ActiveStreaksResponse`` — top-N league-wide active streaks
- ``ApproachingMilestonesResponse`` — career milestones a player is close to
- ``SignaturePerformancesResponse`` — last-game box-score lines that rank in
  the top-N percentile of the player's own career game-log distribution
"""
from __future__ import annotations

from datetime import date as _date
from typing import List, Optional

from pydantic import BaseModel, Field


class PlayerStreakSummary(BaseModel):
    """One active streak row for the league-wide /active-streaks board.

    Captures the streak length, the human-readable streak type label, and
    the qualifying threshold used for detection. ``last_game_on`` and
    ``started_on`` flank the streak window so the UI can render
    "5 straight (since Apr 14)" without recomputing the dates client-side.
    """
    player_id: int
    player_name: str
    team_abbreviation: str
    streak_type: str         # canonical key, e.g. "30plus_pts"
    streak_label: str        # human-readable, e.g. "30+ point games"
    length: int              # consecutive games meeting the criterion
    started_on: Optional[_date] = None
    last_game_on: Optional[_date] = None
    last_game_id: Optional[str] = None
    season: Optional[str] = None


class ActiveStreaksResponse(BaseModel):
    season: str
    streaks: List[PlayerStreakSummary] = Field(default_factory=list)


class MilestoneSnapshotSummary(BaseModel):
    """One approaching-or-achieved career milestone row.

    ``current_value`` is the up-to-date career total (regular season only).
    ``games_to_milestone`` is an estimated games-remaining count derived
    from the player's current-season per-game pace. ``achieved_on`` is
    populated only when the milestone has already been hit; in that case
    ``games_to_milestone`` is null.
    """
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    milestone_key: str           # canonical key, e.g. "10k_pts"
    milestone_label: str         # human-readable, e.g. "10,000 career points"
    threshold: int               # the numerical target, e.g. 10000
    current_value: float         # current career total
    games_to_milestone: Optional[int] = None  # null when achieved
    points_remaining: Optional[float] = None  # threshold - current_value (positive when approaching)
    achieved_on: Optional[_date] = None
    season: Optional[str] = None


class ApproachingMilestonesResponse(BaseModel):
    milestones: List[MilestoneSnapshotSummary] = Field(default_factory=list)


class SignaturePerformance(BaseModel):
    """One signature box-score line.

    A signature performance is a single-game line that ranks in the top-N
    percentile of the player's full career distribution on a chosen
    composite stat (default: pts + 1.2*reb + 1.5*ast). The percentile is
    surfaced so the UI can show "top 8% of his career games" without
    recomputing.
    """
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    game_id: str
    game_date: Optional[_date] = None
    matchup: Optional[str] = None
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    fgm: int = 0
    fga: int = 0
    fg3m: int = 0
    composite_score: float = 0.0
    career_percentile: float = 0.0     # 0..100 — 95.0 means top 5% of career games
    tier: str = "signature"            # "career" (top 5%) | "signature" (top 10%)
    line: str = ""                     # pre-formatted "38/9/7" headline


class SignaturePerformancesResponse(BaseModel):
    date: Optional[_date] = None
    performances: List[SignaturePerformance] = Field(default_factory=list)
