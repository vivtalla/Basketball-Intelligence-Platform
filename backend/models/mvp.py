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
    confidence: Optional[Confidence] = None
    category: Optional[str] = None
    note: Optional[str] = None


class MvpAwardModifier(BaseModel):
    key: str
    label: str
    raw_score: float = 0.0
    modifier: float = 0.0
    display_score: float = 50.0
    confidence: Confidence = "medium"
    category: str = "award_modifier"
    note: Optional[str] = None


class MvpCandidateConfidence(BaseModel):
    overall: Confidence = "medium"
    coverage_score: float = 0.0
    sample_stability_score: float = 0.0
    signal_agreement_score: float = 0.0
    notes: List[str] = Field(default_factory=list)


class MvpQualitativeLens(BaseModel):
    key: str
    label: str
    summary: str
    confidence: Confidence = "medium"
    evidence: List[str] = Field(default_factory=list)


class MvpMethodologyLabel(BaseModel):
    key: str
    label: str
    category: Literal["core_score_input", "award_modifier", "context_signal", "qualitative_lens"]
    description: str


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


class MvpImpactConsensusMetric(BaseModel):
    name: str
    value: Optional[float] = None
    percentile: Optional[float] = None  # 0-100 percentile inside the candidate pool
    source: Optional[str] = None
    as_of: Optional[str] = None
    note: Optional[str] = None


class MvpImpactConsensusProfile(BaseModel):
    """Percentile-averaged consensus across loaded impact metrics. Sprint 52."""
    metrics: List[MvpImpactConsensusMetric] = Field(default_factory=list)
    consensus_score: Optional[float] = None          # 0-100 avg percentile across available metrics
    coverage_ratio: str = "0/0"                       # e.g. "3/6"
    disagreement: Optional[float] = None              # std dev of percentiles; higher = metrics disagree
    note: str = (
        "Impact Consensus averages percentile ranks across the impact metrics we "
        "currently have loaded for this season. Missing metrics are shown so coverage is transparent."
    )


class MvpClutchProfile(BaseModel):
    """Dashboard clutch signals (NBA definition: last 5 min, margin ≤ 5). Sprint 52."""
    clutch_games: Optional[int] = None
    clutch_minutes: Optional[float] = None
    clutch_possessions: Optional[float] = None
    clutch_pts: Optional[float] = None
    clutch_fg_pct: Optional[float] = None
    clutch_fg3_pct: Optional[float] = None
    clutch_ts_pct: Optional[float] = None
    clutch_efg_pct: Optional[float] = None
    clutch_ast_to: Optional[float] = None
    clutch_usg_pct: Optional[float] = None
    clutch_plus_minus: Optional[float] = None
    clutch_net_rating: Optional[float] = None
    clutch_on_off: Optional[float] = None
    close_game_wins: Optional[int] = None
    close_game_losses: Optional[int] = None
    confidence: Confidence = "low"
    source: Optional[str] = None
    note: Optional[str] = None


class MvpOpponentAdjustedBucket(BaseModel):
    bucket: str                      # "top10_def" | "mid_def" | "bottom_def"
    label: str
    games: Optional[int] = None
    pts_per_game: Optional[float] = None
    ts_pct: Optional[float] = None
    plus_minus: Optional[float] = None
    confidence: Confidence = "low"


class MvpOpponentAdjustedProfile(BaseModel):
    buckets: List[MvpOpponentAdjustedBucket] = Field(default_factory=list)
    ts_gap_top_vs_bottom: Optional[float] = None     # delta TS% against top-10 D vs bottom-10 D
    pts_gap_top_vs_bottom: Optional[float] = None
    confidence: Confidence = "low"
    note: str = (
        "Buckets group opponents by season defensive rating tier. "
        "Gaps quantify how a candidate's production holds up against stronger defenses."
    )


class MvpSignatureGame(BaseModel):
    game_id: Optional[str] = None
    date: Optional[str] = None
    opponent: Optional[str] = None
    opponent_drtg_rank: Optional[int] = None
    opponent_tier: Optional[str] = None       # "top10_def" | "mid_def" | "bottom_def"
    result: Optional[str] = None              # "W" | "L"
    pts: Optional[int] = None
    reb: Optional[int] = None
    ast: Optional[int] = None
    ts_pct: Optional[float] = None
    plus_minus: Optional[int] = None
    leverage_score: Optional[float] = None    # higher = bigger stage (opp quality × closeness × volume)


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
    basketball_value_score: Optional[float] = None
    award_case_score: Optional[float] = None
    basketball_value_rank: Optional[int] = None
    award_case_rank: Optional[int] = None
    ballot_eligible_rank: Optional[int] = None
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
    basketball_value_pillars: Dict[str, MvpScorePillar] = Field(default_factory=dict)
    award_modifiers: Dict[str, MvpAwardModifier] = Field(default_factory=dict)
    confidence: Optional[MvpCandidateConfidence] = None
    qualitative_lenses: List[MvpQualitativeLens] = Field(default_factory=list)
    methodology_labels: List[MvpMethodologyLabel] = Field(default_factory=list)
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
    # Sprint 52 additions — holistic context blocks
    impact_consensus: Optional[MvpImpactConsensusProfile] = None
    clutch_profile: Optional[MvpClutchProfile] = None
    opponent_adjusted: Optional[MvpOpponentAdjustedProfile] = None
    signature_games: List[MvpSignatureGame] = Field(default_factory=list)
    rank_by_profile: Dict[str, int] = Field(default_factory=dict)


class MvpRaceResponse(BaseModel):
    season: str
    as_of_date: str                     # ISO date of most-recent game log row used
    candidates: List[MvpCandidate]
    weights: Dict[str, float]           # weights used for this response
    scoring_profile: str = "mvp_case_v2_gravity"
    available_profiles: List[str] = Field(
        default_factory=lambda: ["box_first", "balanced", "impact_consensus"]
    )


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
    available_profiles: List[str] = Field(
        default_factory=lambda: ["box_first", "balanced", "impact_consensus"]
    )


class MvpSensitivityPlayer(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: str
    headshot_url: str = ""
    rank_by_profile: Dict[str, int]
    composite_score_default: Optional[float] = None


class MvpSensitivityResponse(BaseModel):
    season: str
    as_of_date: str
    default_profile: str = "balanced"
    profiles: List[str]
    profile_labels: Dict[str, str] = Field(
        default_factory=lambda: {
            "box_first": "Box-First",
            "balanced": "Balanced",
            "impact_consensus": "Impact-Consensus",
        }
    )
    players: List[MvpSensitivityPlayer]


class MvpTimelinePoint(BaseModel):
    date: str
    rank: int
    score: float
    context_adjusted_score: Optional[float] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    wins: Optional[int] = None
    losses: Optional[int] = None


class MvpTimelinePlayer(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: str
    current_rank: int
    previous_rank: Optional[int] = None
    rank_delta: Optional[int] = None
    current_score: float
    previous_score: Optional[float] = None
    score_delta: Optional[float] = None
    current_context_adjusted_score: Optional[float] = None
    momentum: str = "steady"
    eligibility_status: str = "unknown"
    impact_consensus_score: Optional[float] = None
    clutch_confidence: Optional[Confidence] = None
    gravity_score: Optional[float] = None
    coverage_warning_count: int = 0
    reasons: List[str] = Field(default_factory=list)
    series: List[MvpTimelinePoint] = Field(default_factory=list)


class MvpTimelineMover(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: str
    current_rank: int
    previous_rank: int
    rank_delta: int
    score_delta: Optional[float] = None
    reasons: List[str] = Field(default_factory=list)


class MvpTimelineResponse(BaseModel):
    season: str
    profile: str = "balanced"
    as_of_date: str
    snapshot_count: int = 0
    horizon_start: Optional[str] = None
    horizon_end: Optional[str] = None
    timeline_grain: str = "weekly"
    timeline_mode: str = "value_driven_weekly_reconstruction"
    future_mode: str = "voter_style_ballot_simulation"
    methodology: str = ""
    players: List[MvpTimelinePlayer] = Field(default_factory=list)
    biggest_movers: List[MvpTimelineMover] = Field(default_factory=list)
    coverage_note: str


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
