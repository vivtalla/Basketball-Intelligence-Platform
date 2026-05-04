from typing import Dict, List, Optional

from pydantic import BaseModel

from models.team_fit import FitDriver, OverlapFlag


class TeamNeedFeature(BaseModel):
    feature_key: str
    label: str
    team_z: float
    gap: float
    percentile: float


class TeamNeedVector(BaseModel):
    features: List[TeamNeedFeature]
    primary_needs: List[str]
    primary_strengths: List[str]


class CohortPercentile(BaseModel):
    feature_key: str
    label: str
    percentile: float
    bucket: str


class PlayerFitEntry(BaseModel):
    player_id: int
    full_name: str
    position: Optional[str] = None
    position_bucket: str
    headshot_url: Optional[str] = None
    current_team_abbr: Optional[str] = None
    season: str
    gp: int
    fit_score: float
    skill_supply_score: float
    roster_need_score: float
    role_competition_score: float
    confidence: str
    confidence_notes: List[str] = []
    summary: str
    value_drivers: List[FitDriver] = []
    role_runway_drivers: List[FitDriver] = []
    overlap_flags: List[OverlapFlag] = []
    cohort_percentiles: List[CohortPercentile] = []


class TeamRosterFitMethodology(BaseModel):
    version: str
    weights: Dict[str, float]
    duplicate_threshold: float
    duplicate_penalty: float
    min_team_players: int
    league_candidate_min_gp: int
    position_cohort_enabled: bool
    cohort_buckets: List[str]
    notes: List[str]


class TeamRosterFitResponse(BaseModel):
    team_abbreviation: str
    team_name: Optional[str] = None
    season: str
    season_type: str
    qualified_roster_count: int
    team_need_vector: TeamNeedVector
    current_roster_fits: List[PlayerFitEntry]
    league_candidates: List[PlayerFitEntry]
    methodology: TeamRosterFitMethodology
    warnings: List[str] = []
    generated_at: str
