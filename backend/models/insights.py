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


class OpportunityDriverContribution(BaseModel):
    signal: str  # one of: efficiency_load_gap, team_impact_swing, lineup_synergy_lift, role_fit_gap, cohort_percentile
    z_score: float  # capped [-2.0, 2.0]
    weighted_contribution: float


class OpportunityTeammate(BaseModel):
    teammate_id: int
    teammate_name: str
    shared_possessions: int
    net_rating_with: Optional[float] = None


class OpportunityRoleFit(BaseModel):
    par3: Optional[float] = None           # 3PA rate
    par3_bucket_avg: Optional[float] = None
    ftr: Optional[float] = None            # free throw rate
    ftr_bucket_avg: Optional[float] = None
    efg_pct: Optional[float] = None
    efg_bucket_avg: Optional[float] = None
    ast_pg: Optional[float] = None
    ast_bucket_avg: Optional[float] = None
    tov_pg: Optional[float] = None
    tov_bucket_avg: Optional[float] = None


class OpportunityCompareHandoff(BaseModel):
    """Sprint 65: pre-selected positional peers for a Compare launch from Opportunity."""
    pinned_player_id: int
    positional_peers: List[int] = []       # top cohort peers by opportunity_score (<=3, excludes self)
    cohort_bucket: str                     # position_bucket used for peer selection


class OpportunityPlayerRow(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: str
    position: Optional[str] = None
    position_bucket: str
    minutes_pg: Optional[float] = None
    gp: Optional[int] = None

    # Core stats (also used by frontend cards)
    usg_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    net_rating: Optional[float] = None
    pts_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    tov_pg: Optional[float] = None

    # On/off
    on_off_net: Optional[float] = None
    on_minutes: Optional[float] = None
    off_minutes: Optional[float] = None

    # Lineup synergy
    top_teammate: Optional[OpportunityTeammate] = None

    # Role fit
    role_fit: Optional[OpportunityRoleFit] = None

    # Scoring
    opportunity_score: float
    team_opportunity_score: Optional[float] = None
    cohort_percentile: Optional[float] = None
    confidence: str  # "high" | "medium" | "low"
    driver_contributions: List[OpportunityDriverContribution] = []

    # Hint
    directional_hint: Optional[str] = None
    hint_basis: List[str] = []

    # Classification badge shown on the row — highest positive driver name
    top_driver: Optional[str] = None

    # Sprint 65: pre-computed peer set so Compare launches do not re-query
    compare_handoff: Optional[OpportunityCompareHandoff] = None


class OpportunityMethodology(BaseModel):
    version: str
    weights: Dict[str, float]
    z_score_cap: float
    min_minutes: float
    min_lineup_possessions: int
    confidence_thresholds: Dict[str, Dict[str, float]]
    notes: List[str]


class OpportunityTeamRollup(BaseModel):
    team_abbreviation: str
    top_drivers: Dict[str, int]  # driver_name -> count of players where it was the top driver
    sample_size: int


class OpportunityResponse(BaseModel):
    season: str
    team: Optional[str] = None
    min_minutes: float
    position_filter: Optional[str] = None
    rows: List[OpportunityPlayerRow]
    team_rollup: Optional[OpportunityTeamRollup] = None
    methodology: OpportunityMethodology
    warnings: List[str] = []
