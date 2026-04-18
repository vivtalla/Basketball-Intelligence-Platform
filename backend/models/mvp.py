from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Confidence = Literal["high", "medium", "low"]


class MvpScorePillar(BaseModel):
    label: str
    weight: float
    raw_score: float
    weighted_score: float
    display_score: float


class MvpTeamContext(BaseModel):
    team_id: Optional[int] = None
    team_name: Optional[str] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    win_pct: Optional[float] = None
    net_rating: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    win_pct_rank: Optional[int] = None
    net_rating_rank: Optional[int] = None


class MvpOnOffProfile(BaseModel):
    on_minutes: Optional[float] = None
    off_minutes: Optional[float] = None
    on_net_rating: Optional[float] = None
    off_net_rating: Optional[float] = None
    on_off_net: Optional[float] = None
    on_ortg: Optional[float] = None
    on_drtg: Optional[float] = None
    off_ortg: Optional[float] = None
    off_drtg: Optional[float] = None
    confidence: Confidence = "low"


class MvpAdvancedProfile(BaseModel):
    usg_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    efg_pct: Optional[float] = None
    bpm: Optional[float] = None
    obpm: Optional[float] = None
    dbpm: Optional[float] = None
    vorp: Optional[float] = None
    ws: Optional[float] = None
    win_shares_per_48: Optional[float] = None
    pie: Optional[float] = None
    net_rating: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    epm: Optional[float] = None
    raptor: Optional[float] = None
    lebron: Optional[float] = None


class MvpClutchAndPaceProfile(BaseModel):
    clutch_pts: Optional[float] = None
    clutch_fga: Optional[int] = None
    clutch_fg_pct: Optional[float] = None
    second_chance_pts: Optional[float] = None
    fast_break_pts: Optional[float] = None


class MvpPlayStyleRow(BaseModel):
    action_family: str
    label: str
    usage_share: Optional[float] = None
    points_per_possession: Optional[float] = None
    turnover_rate: Optional[float] = None
    ev_score: Optional[float] = None
    raw_volume: int = 0
    confidence: Confidence = "low"
    note: str


class MvpDataCoverage(BaseModel):
    has_season_stats: bool = False
    has_team_context: bool = False
    has_on_off: bool = False
    has_pbp_splits: bool = False
    has_play_style: bool = False
    has_eligibility: bool = False
    has_opponent_context: bool = False
    has_support_burden: bool = False
    has_external_impact: bool = False
    has_gravity: bool = False
    warnings: List[str] = Field(default_factory=list)


class MvpEligibilityProfile(BaseModel):
    eligibility_status: Literal["eligible", "at_risk", "ineligible", "unknown"] = "unknown"
    eligible_games: int = 0
    games_needed: int = 65
    minutes_qualified_games: int = 0
    near_miss_games: int = 0
    games_played: int = 0
    minutes_played: Optional[float] = None
    warning: Optional[str] = None


class MvpSplitRow(BaseModel):
    key: str
    label: str
    games: int = 0
    wins: Optional[int] = None
    losses: Optional[int] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    plus_minus_pg: Optional[float] = None
    confidence: Confidence = "low"


class MvpOpponentContext(BaseModel):
    rows: List[MvpSplitRow] = Field(default_factory=list)
    best_split: Optional[str] = None
    biggest_weakness: Optional[str] = None
    note: str = "Opponent-quality groups are derived from current team ratings and player game logs."


class MvpSupportBurden(BaseModel):
    candidate_usage_pct: Optional[float] = None
    team_net_without_candidate: Optional[float] = None
    top_teammate_name: Optional[str] = None
    top_teammate_pts_pg: Optional[float] = None
    top_teammate_games: Optional[int] = None
    teammate_availability_avg_gp: Optional[float] = None
    support_note: Optional[str] = None


class MvpImpactMetricCoverage(BaseModel):
    local_metrics: List[str] = Field(default_factory=list)
    external_metrics_present: List[str] = Field(default_factory=list)
    external_metrics_missing: List[str] = Field(default_factory=list)
    note: str


class MvpVisualCoordinates(BaseModel):
    x_team_success: float = 50.0
    y_individual_impact: float = 50.0
    production: float = 50.0
    efficiency: float = 50.0
    availability: float = 0.0
    momentum: float = 50.0
    bubble_size: float = 18.0
    color_key: str = "steady"
    explanation: str


class MvpGravityProfile(BaseModel):
    player_id: int
    source: str = "courtvue_proxy"
    source_label: str = "CourtVue Proxy Gravity"
    overall_gravity: Optional[float] = None
    shooting_gravity: Optional[float] = None
    rim_gravity: Optional[float] = None
    creation_gravity: Optional[float] = None
    roll_or_screen_gravity: Optional[float] = None
    off_ball_gravity: Optional[float] = None
    spacing_lift: Optional[float] = None
    gravity_confidence: Confidence = "low"
    gravity_minutes: Optional[float] = None
    source_note: str
    warnings: List[str] = Field(default_factory=list)


class MvpCandidate(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    headshot_url: str
    gp: int
    composite_score: float          # normalized 0–100 relative to rank-1 player
    context_adjusted_score: Optional[float] = None
    pts_pg: float
    reb_pg: float
    ast_pg: float
    ts_pct: Optional[float] = None
    bpm: Optional[float] = None
    pts_delta: Optional[float] = None   # last-10 avg PTS minus season avg PTS
    reb_delta: Optional[float] = None
    ast_delta: Optional[float] = None
    ts_delta: Optional[float] = None
    momentum: str = "steady"            # "hot" | "cold" | "steady"
    last_games: int = 0                 # count of recent game log rows used
    score_pillars: Dict[str, MvpScorePillar] = Field(default_factory=dict)
    case_summary: List[str] = Field(default_factory=list)
    team_context: Optional[MvpTeamContext] = None
    on_off: Optional[MvpOnOffProfile] = None
    advanced_profile: Optional[MvpAdvancedProfile] = None
    clutch_and_pace: Optional[MvpClutchAndPaceProfile] = None
    play_style: List[MvpPlayStyleRow] = Field(default_factory=list)
    data_coverage: Optional[MvpDataCoverage] = None
    eligibility: Optional[MvpEligibilityProfile] = None
    opponent_context: Optional[MvpOpponentContext] = None
    support_burden: Optional[MvpSupportBurden] = None
    split_profile: List[MvpSplitRow] = Field(default_factory=list)
    impact_metric_coverage: Optional[MvpImpactMetricCoverage] = None
    visual_coordinates: Optional[MvpVisualCoordinates] = None
    gravity_profile: Optional[MvpGravityProfile] = None


class MvpRaceResponse(BaseModel):
    season: str
    as_of_date: str                     # ISO date of most-recent game log row used
    candidates: List[MvpCandidate]
    weights: Dict[str, float]           # weights used for this response
    scoring_profile: str = "mvp_case_v2_gravity"


class MvpNearbyCandidate(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    composite_score: float


class MvpCandidateCaseResponse(BaseModel):
    season: str
    as_of_date: str
    candidate: MvpCandidate
    nearby: List[MvpNearbyCandidate] = Field(default_factory=list)
    weights: Dict[str, float]
    scoring_profile: str = "mvp_case_v2_gravity"


class MvpContextMapPoint(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    composite_score: float
    eligibility_status: str
    momentum: str
    x_team_success: float
    y_individual_impact: float
    production: float
    efficiency: float
    availability: float
    momentum_score: float
    gravity: Optional[float] = None
    bubble_size: float
    color_key: str
    quick_evidence: List[str] = Field(default_factory=list)
    coverage_warnings: List[str] = Field(default_factory=list)


class MvpContextMapResponse(BaseModel):
    season: str
    as_of_date: str
    scoring_profile: str = "mvp_case_v2_gravity"
    default_x: str = "team_success"
    default_y: str = "individual_impact"
    axis_options: List[str] = Field(default_factory=lambda: [
        "team_success",
        "impact",
        "production",
        "efficiency",
        "availability",
        "momentum",
        "gravity",
    ])
    points: List[MvpContextMapPoint]
    methodology: str


class MvpGravityLeaderboardResponse(BaseModel):
    season: str
    as_of_date: str
    source_policy: str
    profiles: List[MvpGravityProfile]
