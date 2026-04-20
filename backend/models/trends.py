from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TrendSeriesPoint(BaseModel):
    label: str
    value: Optional[float] = None


class TrendOverview(BaseModel):
    headline: str
    recent_record: Optional[str] = None
    recent_net_rating: Optional[float] = None
    baseline_net_rating: Optional[float] = None
    recent_ts_pct: Optional[float] = None
    baseline_ts_pct: Optional[float] = None
    recent_pace: Optional[float] = None
    baseline_pace: Optional[float] = None
    games_in_window: int = 0
    player_count: int = 0


class ReplayLaunchTarget(BaseModel):
    source_surface: str
    source_label: str
    reason: str
    target_game_id: str
    target_game_date: Optional[str] = None
    target_opponent_abbreviation: Optional[str] = None
    focus_event_id: Optional[str] = None
    focused_action_number: Optional[int] = None
    linkage_quality: Literal["exact", "derived", "timeline"] = "timeline"
    deep_link_url: str


class TrendCard(BaseModel):
    card_id: str
    title: str
    scope: Literal["team", "player", "lineup"] = "team"
    driver_signal: Optional[str] = None
    direction: Literal["up", "down", "flat"]
    magnitude: Optional[float] = None
    significance: Literal["high", "medium", "low"]
    summary: str
    series: List[TrendSeriesPoint]
    supporting_stats: Dict[str, Optional[float]]
    drilldowns: List[str]
    related_player_ids: List[int] = []
    replay_target: Optional[ReplayLaunchTarget] = None


class TrendDriverContribution(BaseModel):
    signal: str
    label: str
    value: Optional[float] = None
    contribution: float
    note: str


class TrendPlayerRow(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: str
    position: Optional[str] = None
    trend_score: float
    trend_label: str
    primary_signal: str
    confidence: Literal["high", "medium", "low"]
    recent_games: int
    recent_pts_pg: Optional[float] = None
    baseline_pts_pg: Optional[float] = None
    recent_ts_pct: Optional[float] = None
    baseline_ts_pct: Optional[float] = None
    recent_minutes_pg: Optional[float] = None
    baseline_minutes_pg: Optional[float] = None
    on_off_net: Optional[float] = None
    gravity_score: Optional[float] = None
    shot_quality_delta: Optional[float] = None
    driver_contributions: List[TrendDriverContribution] = []
    warnings: List[str] = []


class TrendFoundationSignal(BaseModel):
    signal: str
    label: str
    value: Optional[float] = None
    context: str
    status: Literal["ready", "partial", "missing"] = "ready"


class TrendPlayerDetail(BaseModel):
    row: TrendPlayerRow
    foundation: List[TrendFoundationSignal]
    recent_series: List[TrendSeriesPoint]
    drilldowns: List[str]


class TrendMethodology(BaseModel):
    version: str
    window_games: int
    scoring_inputs: List[str]
    coverage_notes: List[str]


class TrendCardsResponse(BaseModel):
    team_abbreviation: str
    team_name: str
    season: str
    data_status: Literal["ready", "partial", "limited", "missing"] = "missing"
    overview: Optional[TrendOverview] = None
    window_games: int
    cards: List[TrendCard]
    player_movers: List[TrendPlayerRow] = []
    pinned_player: Optional[TrendPlayerDetail] = None
    methodology: Optional[TrendMethodology] = None
    warnings: List[str]


class WhatIfRequest(BaseModel):
    team: str
    season: str
    scenario_type: str
    delta: float
    window: int = 10
    opponent: Optional[str] = None
    context: Dict[str, str] = Field(default_factory=dict)


class WhatIfComparablePattern(BaseModel):
    team_abbreviation: str
    team_name: Optional[str] = None
    season: str
    archetype: Optional[str] = None
    summary: str
    distance: Optional[float] = None


class WhatIfDriverFeature(BaseModel):
    metric_id: str
    label: str
    value: Optional[float] = None
    league_reference: Optional[float] = None
    note: str


class WhatIfStyleImplication(BaseModel):
    archetype: str
    label_reason: str
    stability: str
    opposing_tension: Optional[str] = None
    relevant_contributors: List[str] = Field(default_factory=list)


class WhatIfLaunchLinks(BaseModel):
    prep_url: Optional[str] = None
    compare_url: str
    style_xray_url: str
    replay_url: Optional[str] = None


class WhatIfContext(BaseModel):
    team: str
    season: str
    window: int
    opponent: Optional[str] = None
    source_view: Optional[str] = None
    source_snapshot_id: Optional[str] = None


class WhatIfResponse(BaseModel):
    data_status: Literal["ready", "partial", "limited", "missing"]
    canonical_source: str
    context: WhatIfContext
    team_abbreviation: str
    season: str
    scenario_type: str
    scenario_label: str
    delta: float
    expected_direction: str
    summary: str
    directional_note: Optional[str] = None
    confidence: Literal["high", "medium", "low"]
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    driver_features: List[WhatIfDriverFeature]
    comparable_patterns: List[WhatIfComparablePattern]
    style_implication: WhatIfStyleImplication
    launch_links: WhatIfLaunchLinks
    replay_target: Optional[ReplayLaunchTarget] = None
    warnings: List[str]
