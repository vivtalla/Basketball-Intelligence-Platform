from typing import Dict, List, Optional

from pydantic import BaseModel

from models.methodology import AnalysisMetadata


class FitDriver(BaseModel):
    feature_key: str
    label: str
    player_z: float
    team_need_z: float
    contribution: float
    summary: str


class OverlapFlag(BaseModel):
    feature_key: str
    label: str
    teammate_id: int
    teammate_name: str
    player_z: float
    teammate_z: float
    gap: float
    multiplier: float


class CurrentTeamFit(BaseModel):
    team_abbreviation: str
    fit_score: float
    value_supplied_score: float
    teammate_overlap_score: float
    role_runway_score: float
    skill_supply_score: Optional[float] = None
    roster_need_score: Optional[float] = None
    role_competition_score: Optional[float] = None
    confidence: Optional[str] = None
    confidence_notes: List[str] = []
    summary: str
    value_drivers: List[FitDriver] = []
    role_runway_drivers: List[FitDriver] = []
    overlap_flags: List[OverlapFlag] = []


class AlternativeTeamFit(BaseModel):
    team_abbreviation: str
    team_name: Optional[str] = None
    fit_score: float
    score_delta_vs_current: float
    label: str
    skill_supply_score: Optional[float] = None
    roster_need_score: Optional[float] = None
    role_competition_score: Optional[float] = None
    confidence: Optional[str] = None
    confidence_notes: List[str] = []
    summary: str
    value_drivers: List[FitDriver] = []
    role_runway_drivers: List[FitDriver] = []
    overlap_flags: List[OverlapFlag] = []


class TeamFitMethodology(BaseModel):
    version: str
    weights: Dict[str, float]
    duplicate_threshold: float
    duplicate_penalty: float
    min_games: int
    min_team_players: int
    better_fit_delta_threshold: float
    notes: List[str]


class TeamFitContext(BaseModel):
    team_abbreviation: Optional[str] = None
    overlap_flags: List[OverlapFlag] = []
    summary: Optional[str] = None


class TeamFitResponse(BaseModel):
    player_id: int
    player_name: str
    season: str
    current_team: Optional[CurrentTeamFit] = None
    alternative_teams: List[AlternativeTeamFit] = []
    methodology: TeamFitMethodology
    warnings: List[str] = []
    analysis_metadata: Optional[AnalysisMetadata] = None
