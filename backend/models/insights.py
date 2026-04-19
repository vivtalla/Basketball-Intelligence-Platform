from typing import Dict, List, Optional

from pydantic import BaseModel


class TrajectoryDriverContribution(BaseModel):
    signal: str
    delta: float
    weighted_contribution: float


class TrajectoryEvidenceGame(BaseModel):
    game_id: str
    date: Optional[str] = None
    opponent: Optional[str] = None
    result: Optional[str] = None
    headline_stat: str


class TrajectoryClutchContext(BaseModel):
    clutch_pts: Optional[float] = None
    clutch_fg_pct: Optional[float] = None
    clutch_fga: Optional[int] = None


class TrajectoryOnOffContext(BaseModel):
    on_off_net: Optional[float] = None
    on_minutes: Optional[float] = None
    off_minutes: Optional[float] = None
    confidence: str  # "high", "medium", "low", "insufficient"


class TrajectoryPlayerRow(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team: str
    position: Optional[str] = None
    trajectory_label: str
    trajectory_score: float
    position_percentile: Optional[float] = None
    key_stat_deltas: Dict[str, float]
    driver_contributions: List[TrajectoryDriverContribution] = []
    narrative: str
    context_flags: List[str]
    evidence_games: List[TrajectoryEvidenceGame] = []
    clutch_context: Optional[TrajectoryClutchContext] = None
    on_off_context: Optional[TrajectoryOnOffContext] = None
    recent_averages: Dict[str, Optional[float]] = {}
    baseline_averages: Dict[str, Optional[float]] = {}


class TrajectoryResponse(BaseModel):
    window: str
    breakout_leaders: List[TrajectoryPlayerRow]
    decline_watch: List[TrajectoryPlayerRow]
    excluded_players: List[str]
    warnings: List[str]


class TrajectorySeriesGame(BaseModel):
    game_id: str
    date: Optional[str] = None
    pts: Optional[float] = None
    reb: Optional[float] = None
    ast: Optional[float] = None
    ts_pct: Optional[float] = None
    usg_pct: Optional[float] = None
    plus_minus: Optional[float] = None
    is_recent: bool


class TrajectorySeriesResponse(BaseModel):
    player_id: int
    player_name: str
    season: str
    series: List[TrajectorySeriesGame]


class TeammateOnOff(BaseModel):
    teammate_id: int
    teammate_name: str
    shared_minutes: Optional[float] = None
    possessions: Optional[int] = None
    net_rating_with: Optional[float] = None
    confidence: str  # "high", "medium", "low", "insufficient"


class LineupContextResponse(BaseModel):
    player_id: int
    player_name: str
    season: str
    on_off_net: Optional[float] = None
    on_minutes: Optional[float] = None
    off_minutes: Optional[float] = None
    top_teammates: List[TeammateOnOff] = []
    notes: List[str] = []


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
