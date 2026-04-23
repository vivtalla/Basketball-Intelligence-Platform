from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class LineupImpactFilters(BaseModel):
    season: str
    opponent_abbreviation: Optional[str] = None
    window_games: int
    min_possessions: int


class LineupImpactRow(BaseModel):
    lineup_key: str
    player_ids: List[int]
    player_names: List[str]
    minutes: Optional[float] = None
    possessions: Optional[int] = None
    observed_net_rating: Optional[float] = None
    shrunk_net_rating: Optional[float] = None
    expected_points_per_100: Optional[float] = None
    expected_points_per_game: Optional[float] = None
    minute_delta: Optional[float] = None
    confidence: Literal["high", "medium", "low"]
    evidence: List[str]


class LineupImpactResponse(BaseModel):
    team_abbreviation: str
    season: str
    filters: LineupImpactFilters
    current_rotation: List[LineupImpactRow]
    recommended_rotation: List[LineupImpactRow]
    lineup_rows: List[LineupImpactRow]
    impact_summary: str
    confidence: Literal["high", "medium", "low"]
    warnings: List[str]


class PlayTypeEVFilters(BaseModel):
    season: str
    opponent_abbreviation: Optional[str] = None
    window_games: int


class PlayTypeEVRow(BaseModel):
    action_family: str
    label: str
    usage_share: Optional[float] = None
    points_per_possession: Optional[float] = None
    turnover_rate: Optional[float] = None
    foul_rate: Optional[float] = None
    offensive_rebound_rate: Optional[float] = None
    ev_score: Optional[float] = None
    league_percentile: Optional[float] = None
    note: str


class PlayTypeFlag(BaseModel):
    action_family: str
    label: str
    reason: str
    severity: Literal["high", "medium", "low"]
    confidence: Literal["high", "medium", "low"]
    evidence: List[str]


class PlayTypeEVResponse(BaseModel):
    team_abbreviation: str
    season: str
    filters: PlayTypeEVFilters
    action_rows: List[PlayTypeEVRow]
    overused_flags: List[PlayTypeFlag]
    underused_flags: List[PlayTypeFlag]
    warnings: List[str]


class MatchupFlagEvidence(BaseModel):
    metric_id: str
    label: str
    team_value: Optional[float] = None
    opponent_value: Optional[float] = None
    league_reference: Optional[float] = None
    note: str


class MatchupFlag(BaseModel):
    flag_id: str
    title: str
    summary: str
    severity: Literal["high", "medium", "low"]
    confidence: Literal["high", "medium", "low"]
    evidence: List[MatchupFlagEvidence]
    drilldowns: List[str]


class MatchupFlagsResponse(BaseModel):
    team_abbreviation: str
    opponent_abbreviation: str
    season: str
    flags: List[MatchupFlag]
    warnings: List[str]


class FollowThroughRequest(BaseModel):
    source_type: str
    source_id: str
    team: str
    opponent: Optional[str] = None
    player_ids: List[int] = Field(default_factory=list)
    lineup_key: Optional[str] = None
    season: str
    window: int = 10
    context: Dict[str, str] = Field(default_factory=dict)


class FollowThroughGame(BaseModel):
    game_id: str
    game_date: Optional[str] = None
    opponent_abbreviation: Optional[str] = None
    result: Optional[str] = None
    why_this_game: str
    relevance_score: float
    supporting_metrics: List[str]
    deep_link_url: str


class FollowThroughResponse(BaseModel):
    source_type: str
    source_id: str
    team_abbreviation: str
    opponent_abbreviation: Optional[str] = None
    season: str
    window: int
    games: List[FollowThroughGame]
    warnings: List[str]


class OpponentPlayTypeRow(BaseModel):
    play_type: str
    poss_pct: Optional[float] = None
    ppp: Optional[float] = None
    percentile: Optional[float] = None
    fg_pct: Optional[float] = None
    score_pct: Optional[float] = None


class OpponentPlayTypeResponse(BaseModel):
    team_abbr: str
    season: str
    plays: List[OpponentPlayTypeRow]
    data_status: str
    source: str = "synergy"


class H2HGame(BaseModel):
    game_id: str
    game_date: Optional[str] = None
    season: str
    is_home: bool
    team_score: Optional[int] = None
    opponent_score: Optional[int] = None
    margin: Optional[int] = None
    result: str


class H2HResponse(BaseModel):
    team_abbr: str
    opponent_abbr: str
    seasons_covered: List[str]
    wins: int
    losses: int
    series_record: str
    avg_margin: Optional[float] = None
    last_meeting_date: Optional[str] = None
    last_meeting_result: Optional[str] = None
    games: List[H2HGame]
    data_status: str


class PaceEdge(BaseModel):
    team_pace: Optional[float] = None
    opponent_pace: Optional[float] = None
    pace_delta: Optional[float] = None
    framing: str
    edge_label: str
    magnitude: str
