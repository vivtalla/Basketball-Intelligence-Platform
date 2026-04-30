"""Pydantic schemas for the FO3 Draft Prospect Workspace (Sprint 78).

The router returns `ProspectBoardResponse` for the board route and
`ProspectDetail` for the per-prospect deep dive.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CollegeStatLine(BaseModel):
    """Per-game pre-NBA line as it lives in `draft_prospect_stats`."""
    season: str
    league: str
    team_name: Optional[str] = None
    gp: Optional[int] = None
    min_pg: Optional[float] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    stl_pg: Optional[float] = None
    blk_pg: Optional[float] = None
    tov_pg: Optional[float] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    ft_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None
    pace: Optional[float] = None


class NbaTranslation(BaseModel):
    """Pace-adjusted projection of pre-NBA per-game stats onto an NBA per-100 line.

    Pace adjustment: NBA ≈ 100 possessions/48; college ≈ 70 possessions/40.
    Multiplier = NBA_PACE / college_pace; per-game stats are scaled directly.
    `translation_confidence` is a 0..1 heuristic combining sample size,
    league strength, and the ratio between college and NBA pace.
    """
    source_season: str
    source_league: str
    college_pace: float
    nba_pace: float = 100.0
    pace_multiplier: float
    projected_pts_per100: Optional[float] = None
    projected_reb_per100: Optional[float] = None
    projected_ast_per100: Optional[float] = None
    projected_stl_per100: Optional[float] = None
    projected_blk_per100: Optional[float] = None
    projected_tov_per100: Optional[float] = None
    projected_ts_pct: Optional[float] = None
    projected_usg_pct: Optional[float] = None
    translation_confidence: float = Field(
        0.0, ge=0.0, le=1.0,
        description="0..1 confidence that this translation should be trusted.",
    )
    confidence_factors: List[str] = []


class NbaComp(BaseModel):
    """One NBA-comparable veteran for a draft prospect."""
    player_id: int
    player_name: str
    headshot_url: Optional[str] = None
    season: str
    team_abbreviation: Optional[str] = None
    similarity_score: float = Field(..., ge=0.0, le=100.0)
    archetype_label: Optional[str] = None
    rationale: str
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None


class MeasurementPanel(BaseModel):
    """Combine + workout measurements (lightweight fallback to listed h/w/wingspan)."""
    height_no_shoes: Optional[float] = None
    height_with_shoes: Optional[float] = None
    weight: Optional[float] = None
    wingspan: Optional[float] = None
    standing_reach: Optional[float] = None
    standing_vert: Optional[float] = None
    max_vert: Optional[float] = None
    lane_agility_seconds: Optional[float] = None
    three_quarter_sprint_seconds: Optional[float] = None
    source: Optional[str] = None


class DraftProspectSummary(BaseModel):
    """One row on the prospect board."""
    prospect_id: int
    external_id: str
    full_name: str
    draft_year: int
    age_on_draft_day: Optional[float] = None
    height_inches: Optional[float] = None
    weight_lbs: Optional[float] = None
    primary_position: Optional[str] = None
    school: Optional[str] = None
    school_type: Optional[str] = None
    consensus_rank: Optional[int] = None
    headshot_url: Optional[str] = None
    archetype_label: Optional[str] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None


class ProspectBoardResponse(BaseModel):
    draft_year: int
    count: int
    prospects: List[DraftProspectSummary] = []


class ProspectDetail(BaseModel):
    summary: DraftProspectSummary
    bio: Optional[str] = None
    college_stats: List[CollegeStatLine] = []
    translation: Optional[NbaTranslation] = None
    measurement: Optional[MeasurementPanel] = None
    nba_comps: List[NbaComp] = []
