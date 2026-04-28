from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from models.trends import ReplayLaunchTarget


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
    quality: Literal["high", "medium", "low"] = "medium"
    net_rating: Optional[float] = None
    summary: str
    matchup_label: Optional[str] = None


class StyleShotProfileDriver(BaseModel):
    split_family: str
    family_label: Optional[str] = None
    split_value: str
    label: str
    attempt_share: Optional[float] = None
    efg_pct: Optional[float] = None
    league_delta: Optional[float] = None
    summary: str
    trust_level: Literal["strong", "caution"] = "strong"
    trust_note: Optional[str] = None
    strong_claim: bool = True


class StyleFeatureMovement(BaseModel):
    metric_id: str
    label: str
    baseline_z: Optional[float] = None
    recent_z: Optional[float] = None
    delta_z: Optional[float] = None
    direction: Literal["gaining", "stable", "fading"]


class StyleMovement(BaseModel):
    narrative: str
    drift_archetype: Optional[str] = None
    window_games: int
    features: List[StyleFeatureMovement]


class StyleHistoryPoint(BaseModel):
    label: str
    archetype: str
    confidence: Literal["high", "medium", "low"] = "medium"
    record: Optional[str] = None
    shot_profile_note: Optional[str] = None


class StyleScenarioLink(BaseModel):
    scenario_type: str
    title: str
    delta: float
    rationale: str
    what_if_payload: Dict[str, str]


class StyleLaunchLinks(BaseModel):
    prep_url: Optional[str] = None
    compare_url: str
    what_if_url: Optional[str] = None
    replay_url: Optional[str] = None


class StyleLatentLoading(BaseModel):
    """Coach-readable description of a single PCA axis: which features push
    a team toward the positive direction and how strongly.
    """

    feature_id: str
    label: str
    loading: float


class StyleLatentAxis(BaseModel):
    """A principal axis of league-wide stylistic variation. Loadings are the
    feature weights that define the axis; `subject_coordinate` is where the
    current team sits along it after centering. `explained_variance_ratio`
    is the share of total stylistic variance the axis captures.
    """

    axis: str  # "PC1", "PC2", ...
    explained_variance_ratio: float
    subject_coordinate: float
    top_positive: List[StyleLatentLoading]
    top_negative: List[StyleLatentLoading]


class StyleLatentSpace(BaseModel):
    """Latent-space view of league style structure (style_xray_v2). Built from
    the league's current-season style vectors using PCA; complements the
    centroid-based archetype label rather than replacing it.
    """

    sample_size: int
    feature_count: int
    axes: List[StyleLatentAxis]
    interpretation: str


class StyleXRayResponse(BaseModel):
    data_status: Literal["ready", "partial", "limited", "missing"]
    canonical_source: str
    team_abbreviation: str
    team_name: str
    season: str
    window_games: int
    archetype: str
    archetype_confidence: Literal["high", "medium", "low"] = "medium"
    label_reason: str
    feature_contributors: List[StyleFeatureContributor]
    nearest_neighbors: List[StyleNeighbor]
    adjacent_archetypes: List[StyleNeighbor]
    shot_profile_drivers: List[StyleShotProfileDriver] = Field(default_factory=list)
    stability: Literal["stable", "watch", "shifted"]
    movement: Optional[StyleMovement] = None
    history: List[StyleHistoryPoint] = Field(default_factory=list)
    scenario_links: List[StyleScenarioLink]
    launch_links: StyleLaunchLinks
    source_context: Optional[Dict[str, str]] = None
    replay_target: Optional[ReplayLaunchTarget] = None
    warnings: List[str]
    latent_space: Optional[StyleLatentSpace] = None


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
    shot_profile_drivers: List[StyleShotProfileDriver] = Field(default_factory=list)


class StyleComparisonResponse(BaseModel):
    season: str
    entity_a: StyleComparisonEntity
    entity_b: StyleComparisonEntity
    rows: List[ComparisonMetricRow]
    stories: List[ComparisonStory]
    source_context: Optional[Dict[str, str]] = None
