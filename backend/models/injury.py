"""Pydantic schemas for the FO5 Injury Impact + Duration Model surface.

Sprint 78 FO5. Distinct from the existing `InjuryEntry` / `InjuryReportResponse`
in `routers/injuries.py`, which describe current CDN injury report rows.
The schemas here describe model output: an empirical duration distribution,
similar past injuries, and team-availability-impact projections.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class DurationEstimate(BaseModel):
    """Empirical games-missed distribution for a (body_part, age, recurrence) cohort."""

    body_part: str
    sample_size: int
    median_games: int
    p25_games: int
    p75_games: int
    mean_games: float
    is_fallback: bool
    fallback_reason: Optional[str] = None
    cohort_age_low: Optional[float] = None
    cohort_age_high: Optional[float] = None
    cohort_recurrence: Optional[bool] = None


class SimilarPastInjury(BaseModel):
    """One concrete historical injury used as an anchor for the estimate."""

    player_id: int
    player_name: str
    season: Optional[str] = None
    body_part: str
    severity: Optional[str] = None
    started_on: date
    resolved_on: Optional[date] = None
    games_missed: Optional[int] = None
    age_at_start: Optional[float] = None
    is_recurring: bool = False


class PlayerDurationEstimateResponse(BaseModel):
    """Top-level response for /api/injuries/{player_id}/duration-estimate."""

    player_id: int
    player_name: str
    body_part: Optional[str] = None
    severity: Optional[str] = None
    age: Optional[float] = None
    is_recurring: Optional[bool] = None
    current_injury_status: Optional[str] = None
    current_injury_detail: Optional[str] = None
    current_injury_report_date: Optional[date] = None
    current_injury_return_date: Optional[date] = None
    estimate: DurationEstimate
    similar_past_injuries: List[SimilarPastInjury]
    methodology_note: str


class PlayerAvailabilityProjection(BaseModel):
    """Per-player projection feeding into TeamAvailabilityImpact."""

    player_id: int
    player_name: str
    position: str
    injury_status: Optional[str] = None
    injury_type: Optional[str] = None
    detail: Optional[str] = None
    body_part: Optional[str] = None
    season_pts_pg: Optional[float] = None
    season_min_pg: Optional[float] = None
    season_bpm: Optional[float] = None
    on_off_net: Optional[float] = None
    expected_duration: Optional[DurationEstimate] = None
    impact_label: str
    impact_score: float


class RotationReplacement(BaseModel):
    """One projected replacement role on the revised rotation."""

    out_player_id: int
    out_player_name: str
    out_min_pg: Optional[float] = None
    replacement_player_id: Optional[int] = None
    replacement_player_name: Optional[str] = None
    replacement_min_pg: Optional[float] = None
    additional_minutes: Optional[float] = None
    note: str


class TeamAvailabilityImpact(BaseModel):
    """Top-level response for /api/injuries/team/{team_abbr}/availability-impact."""

    team_id: int
    abbreviation: str
    name: str
    season: str
    report_date: Optional[date] = None
    out_count: int
    questionable_count: int
    sidelined_minutes_per_game: float
    sidelined_pts_per_game: float
    net_rating_delta: Optional[float] = None
    healthy_net_rating: Optional[float] = None
    projected_net_rating: Optional[float] = None
    sidelined_players: List[PlayerAvailabilityProjection]
    rotation_replacements: List[RotationReplacement]
    summary: str
