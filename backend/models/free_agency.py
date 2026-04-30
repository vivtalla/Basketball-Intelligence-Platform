"""Sprint 78 — FO2 Free Agency Workspace response schemas.

Pydantic v2 models for the `/api/free-agency` endpoints. The backing data lives
in `PlayerContract` (Phase-0 schema) joined to `Player` and `SeasonStat`. Every
field that depends on optional source data is `Optional` so the workspace
renders gracefully when ingestion has not populated `player_contracts` yet.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


FreeAgentTier = Literal["max", "above_mid", "mid_level", "minimum", "two_way"]


class ExpiringContract(BaseModel):
    """One row in the league-wide expiring-contract leaderboard."""

    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    team_id: Optional[int] = None
    position: Optional[str] = None
    age: Optional[int] = None

    # Contract context
    season: str
    salary: Optional[int] = None
    years_remaining: Optional[int] = None
    is_player_option: bool = False
    is_team_option: bool = False
    is_non_guaranteed: bool = False
    no_trade_clause: bool = False
    contract_type: Optional[str] = None
    expires_on: Optional[str] = None  # ISO yyyy-mm-dd

    tier: FreeAgentTier

    # Production context (latest qualified SeasonStat, if any)
    stat_season: Optional[str] = None
    gp: Optional[int] = None
    min_pg: Optional[float] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None
    net_rating: Optional[float] = None

    # Source attribution
    source: Optional[str] = None


class FitRationaleChip(BaseModel):
    """One short rationale chip explaining a team-fit ranking."""

    label: str
    detail: Optional[str] = None
    contribution: Optional[float] = None


class TeamFitForPlayer(BaseModel):
    """One ranked team-fit row for a free agent."""

    rank: int
    team_abbreviation: str
    team_name: Optional[str] = None
    fit_score: float
    skill_supply_score: Optional[float] = None
    roster_need_score: Optional[float] = None
    role_competition_score: Optional[float] = None
    confidence: Optional[str] = None
    summary: Optional[str] = None
    rationale_chips: List[FitRationaleChip] = []


class FreeAgencyMethodology(BaseModel):
    version: str = "free_agency_v1"
    tier_thresholds_usd: Dict[str, int]
    notes: List[str]


class FreeAgencyResponse(BaseModel):
    season: str
    total_count: int
    filtered_count: int
    contracts: List[ExpiringContract] = []
    available_tiers: List[FreeAgentTier] = []
    methodology: FreeAgencyMethodology
    is_empty_dataset: bool = False
    warnings: List[str] = []


class FreeAgentFitsResponse(BaseModel):
    player_id: int
    player_name: str
    season: str
    contract: Optional[ExpiringContract] = None
    fits: List[TeamFitForPlayer] = []
    warnings: List[str] = []
