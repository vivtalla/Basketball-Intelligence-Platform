"""Pydantic schemas for the Sprint 78 CF3 Career Hall of Fame view.

The career-legacy response is composed of four sub-blocks that the
frontend Legacy tab renders independently:

- ``era_adjusted_summary`` — a single career line with era-adjusted PPG
  (pace-normalized) and TS%-vs-league delta
- ``milestones_achieved`` / ``next_milestone`` — career milestones tied
  to the milestone-snapshot table when populated; computed live otherwise
- ``era_peers`` — 5–10 best-comparable players across all NBA history
  using era-adjusted similarity
- ``hof_projection`` — a simple composite score (0..100) with a label
  band and the top three contributing drivers

All fields are ``Optional`` where the underlying data could be missing,
matching the resilient-assembler pattern used by Sprint 77's game-detail
response.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EraAdjustedSummary(BaseModel):
    """Single-career era-adjusted scoring + efficiency summary.

    ``pts_pg_era_adj`` divides raw PPG by the season's pace ratio
    (league-avg pace / 100), so a 1980s 30-PPG scorer compares more
    fairly to a 2020s 30-PPG scorer. ``ts_pct_delta_vs_league_avg`` is
    the career-weighted average TS% minus the career-weighted league
    baseline, expressed in absolute TS% (e.g. +0.045 == +4.5pp).
    """
    pts_pg: Optional[float] = None
    pts_pg_era_adj: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    ts_pct_delta_vs_league_avg: Optional[float] = None
    games_played: int = 0
    seasons_played: int = 0


class MilestoneAchievement(BaseModel):
    milestone_key: str
    milestone_label: str
    threshold: int
    achieved_on: Optional[_date] = None
    achieved_in_season: Optional[str] = None
    current_value: Optional[float] = None


class MilestoneApproach(BaseModel):
    milestone_key: str
    milestone_label: str
    threshold: int
    current_value: float
    points_remaining: float
    games_to_milestone: Optional[int] = None


class EraPeer(BaseModel):
    """One era-adjusted similarity comp.

    ``similarity_score`` is the converted-from-distance 0..100 score
    used by the existing similarity service. ``comp_basis`` is a short
    chip label describing what makes the comp register
    ("similar volume scorer", "similar shooting profile", etc.).
    """
    player_id: int
    player_name: str
    headshot_url: Optional[str] = None
    seasons_played: int = 0
    similarity_score: float
    comp_basis: str


class HofProjection(BaseModel):
    """Composite legacy projection.

    ``score`` is 0..100. ``label`` bands: 80+ "Likely HOF", 50–79
    "Borderline", <50 "Tracking". ``drivers`` lists the top three
    contributing reasons in descending point-contribution order.
    """
    label: str
    score: int
    drivers: List[str] = Field(default_factory=list)


class CareerLegacyResponse(BaseModel):
    player_id: int
    player_name: str
    seasons_played: int
    era_adjusted_summary: EraAdjustedSummary
    milestones_achieved: List[MilestoneAchievement] = Field(default_factory=list)
    next_milestone: Optional[MilestoneApproach] = None
    era_peers: List[EraPeer] = Field(default_factory=list)
    hof_projection: HofProjection
    methodology_version: str = "career_legacy_v1"

    # Optional metadata block for client-side methodology popovers; kept
    # loose so the frontend can surface whatever the service emits.
    methodology: Optional[Dict[str, Any]] = None
