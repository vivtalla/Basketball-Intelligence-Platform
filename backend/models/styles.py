from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class StyleMetricRow(BaseModel):
    metric_id: str
    label: str
    team_value: Optional[float] = None
    recent_value: Optional[float] = None
    league_reference: Optional[float] = None
    recent_delta: Optional[float] = None
    percentile: Optional[float] = None
    note: str


class ComparisonMetricRow(BaseModel):
    stat_id: str
    label: str
    entity_a_value: Optional[float] = None
    entity_b_value: Optional[float] = None
    higher_better: bool
    format: Literal["number", "percent", "signed"]
    edge: Literal["entity_a", "entity_b", "even"]


class ComparisonStory(BaseModel):
    label: str
    summary: str
    edge: Literal["entity_a", "entity_b", "even"]


class StyleScenarioBin(BaseModel):
    label: str
    direction: Literal["up", "down", "flat"]
    sample_size: int
    avg_net_rating: Optional[float] = None
    avg_points_for: Optional[float] = None
    summary: str


class TeamStyleProfileResponse(BaseModel):
    team_abbreviation: str
    team_name: str
    season: str
    window_games: int
    current_profile: List[StyleMetricRow]
    recent_drift: List[StyleMetricRow]
    league_context: List[StyleMetricRow]
    opponent_comparison: List[ComparisonMetricRow] = Field(default_factory=list)
    scenario_bins: List[StyleScenarioBin]
    warnings: List[str]


class StyleFeatureContributor(BaseModel):
    metric_id: str
    label: str
    value: Optional[float] = None
    share: Optional[float] = None
    note: str


class StyleNeighbor(BaseModel):
    team_abbreviation: str
    team_name: str
    archetype: str
    distance: float
    net_rating: Optional[float] = None
    summary: str


class StyleXRayResponse(BaseModel):
    team_abbreviation: str
    team_name: str
    season: str
    archetype: str
    label_reason: str
    feature_contributors: List[StyleFeatureContributor]
    nearest_neighbors: List[StyleNeighbor]
    adjacent_archetypes: List[StyleNeighbor]
    stability: Literal["stable", "watch", "shifted"]
    warnings: List[str]


class LineupComparisonEntity(BaseModel):
    lineup_key: str
    player_ids: List[int]
    player_names: List[str]
    team_abbreviation: Optional[str] = None
    minutes: Optional[float] = None
    possessions: Optional[int] = None
    net_rating: Optional[float] = None
    ortg: Optional[float] = None
    drtg: Optional[float] = None
    plus_minus: Optional[float] = None


class LineupComparisonResponse(BaseModel):
    season: str
    team: Optional[str] = None
    entity_a: LineupComparisonEntity
    entity_b: LineupComparisonEntity
    rows: List[ComparisonMetricRow]
    stories: List[ComparisonStory]
    source_context: Optional[Dict[str, str]] = None


class StyleComparisonEntity(BaseModel):
    abbreviation: str
    name: str
    season: str
    archetype: str
    label_reason: str
    current_profile: List[StyleMetricRow]


class StyleComparisonResponse(BaseModel):
    season: str
    entity_a: StyleComparisonEntity
    entity_b: StyleComparisonEntity
    rows: List[ComparisonMetricRow]
    stories: List[ComparisonStory]
    source_context: Optional[Dict[str, str]] = None
