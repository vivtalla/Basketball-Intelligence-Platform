from typing import Dict, List, Optional

from pydantic import BaseModel


class TrajectoryPlayerRow(BaseModel):
    rank: int
    player_name: str
    team: str
    trajectory_label: str
    trajectory_score: float
    key_stat_deltas: Dict[str, float]
    narrative: str
    context_flags: List[str]


class TrajectoryResponse(BaseModel):
    window: str
    breakout_leaders: List[TrajectoryPlayerRow]
    decline_watch: List[TrajectoryPlayerRow]
    excluded_players: List[str]
    warnings: List[str]


class UsageEfficiencyPlayerRow(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: str
    minutes_pg: Optional[float] = None
    usg_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    off_rating: Optional[float] = None
    pts_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    tov_pg: Optional[float] = None
    burden_score: Optional[float] = None
    efficiency_score: Optional[float] = None
    category: str


class UsageEfficiencySuggestion(BaseModel):
    player_name: str
    category: str
    suggestion: str


class UsageEfficiencyResponse(BaseModel):
    season: str
    team: Optional[str] = None
    min_minutes: float
    overused_inefficients: List[UsageEfficiencyPlayerRow]
    underused_efficients: List[UsageEfficiencyPlayerRow]
    suggestions: List[UsageEfficiencySuggestion]
    warnings: List[str]
