from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class TrendSeriesPoint(BaseModel):
    label: str
    value: Optional[float] = None


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
    direction: Literal["up", "down", "flat"]
    magnitude: Optional[float] = None
    significance: Literal["high", "medium", "low"]
    summary: str
    series: List[TrendSeriesPoint]
    supporting_stats: Dict[str, Optional[float]]
    drilldowns: List[str]
    replay_target: Optional[ReplayLaunchTarget] = None


class TrendCardsResponse(BaseModel):
    team_abbreviation: str
    team_name: str
    season: str
    window_games: int
    cards: List[TrendCard]
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
