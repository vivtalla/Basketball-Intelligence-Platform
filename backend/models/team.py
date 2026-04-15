from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel

from models.stats import LineupStatsResponse


class TeamRosterPlayer(BaseModel):
    player_id: int
    full_name: str
    position: str
    jersey: str
    headshot_url: str
    season: Optional[str] = None
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    per: Optional[float] = None
    bpm: Optional[float] = None


class TeamRosterResponse(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    players: List[TeamRosterPlayer]
    synced_count: int


class TeamSummary(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    player_count: int


class TeamAnalytics(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    season: str
    canonical_source: Optional[str] = None
    last_synced_at: Optional[str] = None
    gp: int
    w: int
    l: int
    w_pct: float
    pts_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    tov_pg: Optional[float] = None
    blk_pg: Optional[float] = None
    stl_pg: Optional[float] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    ft_pct: Optional[float] = None
    plus_minus_pg: Optional[float] = None
    off_rating: Optional[float] = None
    def_rating: Optional[float] = None
    net_rating: Optional[float] = None
    pace: Optional[float] = None
    efg_pct: Optional[float] = None
    ts_pct: Optional[float] = None
    pie: Optional[float] = None
    oreb_pct: Optional[float] = None
    dreb_pct: Optional[float] = None
    tov_pct: Optional[float] = None
    ast_pct: Optional[float] = None
    off_rating_rank: Optional[int] = None
    def_rating_rank: Optional[int] = None
    net_rating_rank: Optional[int] = None
    pace_rank: Optional[int] = None
    efg_pct_rank: Optional[int] = None
    ts_pct_rank: Optional[int] = None
    oreb_pct_rank: Optional[int] = None
    tov_pct_rank: Optional[int] = None


class TeamSplitRow(BaseModel):
    split_family: str
    split_value: str
    label: str
    gp: int = 0
    w: int = 0
    l: int = 0
    w_pct: float = 0.0
    min: Optional[float] = None
    pts: Optional[float] = None
    reb: Optional[float] = None
    ast: Optional[float] = None
    tov: Optional[float] = None
    stl: Optional[float] = None
    blk: Optional[float] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    ft_pct: Optional[float] = None
    plus_minus: Optional[float] = None


class TeamSplitsResponse(BaseModel):
    team_id: int
    abbreviation: str
    season: str
    canonical_source: Optional[str] = None
    last_synced_at: Optional[str] = None
    splits: List[TeamSplitRow]


class TeamRecentGame(BaseModel):
    game_id: str
    game_date: Optional[str] = None
    opponent_abbreviation: Optional[str] = None
    is_home: bool
    result: str
    team_score: Optional[int] = None
    opponent_score: Optional[int] = None
    margin: Optional[int] = None


class TeamPbpCoverage(BaseModel):
    season: str
    eligible_games: int = 0
    synced_games: int = 0
    players_with_on_off: int = 0
    players_with_scoring_splits: int = 0
    status: str


class TeamImpactLeader(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    on_off_net: Optional[float] = None
    on_minutes: Optional[float] = None
    bpm: Optional[float] = None
    pts_pg: Optional[float] = None
    clutch_pts: Optional[float] = None


class TeamRotationPlayerRow(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    starts_last_10: int = 0
    avg_minutes_last_10: Optional[float] = None
    avg_minutes_season: Optional[float] = None
    minutes_delta: Optional[float] = None
    is_primary_starter: bool = False


class TeamRotationGame(BaseModel):
    game_id: str
    game_date: Optional[str] = None
    opponent_abbreviation: Optional[str] = None
    result: str
    team_score: Optional[int] = None
    opponent_score: Optional[int] = None
    rotation_note: str


class TeamRotationReport(BaseModel):
    team_id: int
    abbreviation: str
    season: str
    status: str
    window_games: int = 0
    starter_stability: str
    recent_starters: List[TeamRotationPlayerRow]
    minute_load_leaders: List[TeamRotationPlayerRow]
    rotation_risers: List[TeamRotationPlayerRow]
    rotation_fallers: List[TeamRotationPlayerRow]
    on_off_anchors: List[TeamImpactLeader]
    recommended_games: List[TeamRotationGame]


class TeamIntelligenceResponse(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    season: str
    data_status: str
    canonical_source: str
    runtime_policy: Optional[str] = None
    last_synced_at: Optional[str] = None
    conference: Optional[str] = None
    playoff_rank: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    win_pct: Optional[float] = None
    l10: Optional[str] = None
    current_streak: Optional[str] = None
    pts_pg: Optional[float] = None
    opp_pts_pg: Optional[float] = None
    diff_pts_pg: Optional[float] = None
    recent_record: Optional[str] = None
    recent_avg_margin: Optional[float] = None
    pbp_coverage: TeamPbpCoverage
    impact_leaders: List[TeamImpactLeader]
    best_lineups: List[LineupStatsResponse]
    worst_lineups: List[LineupStatsResponse]
    recent_games: List[TeamRecentGame]


class TeamPrepQueueItem(BaseModel):
    game_id: str
    game_date: Optional[date] = None
    status: str
    prep_urgency: str
    prep_headline: str
    urgency_rationale: Optional[str] = None
    opponent_abbreviation: Optional[str] = None
    opponent_name: Optional[str] = None
    is_home: bool
    opponent_record: Optional[str] = None
    opponent_conference: Optional[str] = None
    opponent_playoff_rank: Optional[int] = None
    availability_summary: str
    unavailable_count: int = 0
    questionable_count: int = 0
    probable_count: int = 0
    team_rest_days: Optional[int] = None
    opponent_rest_days: Optional[int] = None
    rest_advantage: Optional[int] = None
    schedule_pressure: str
    best_edge_label: Optional[str] = None
    best_edge_summary: Optional[str] = None
    best_edge_rationale: Optional[str] = None
    best_edge_factor_id: Optional[str] = None
    first_adjustment_label: Optional[str] = None
    first_adjustment_summary: Optional[str] = None
    first_adjustment_rationale: Optional[str] = None
    first_adjustment_factor_id: Optional[str] = None
    pre_read_url: str
    scouting_url: str
    compare_url: str
    follow_through_url: str
    game_review_url: str
    latest_snapshot_id: Optional[str] = None
    latest_snapshot_share_url: Optional[str] = None


class TeamPrepQueueResponse(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    season: str
    data_status: str
    canonical_source: str
    runtime_policy: Optional[str] = None
    generated_at: Optional[str] = None
    items: List[TeamPrepQueueItem]


class TeamFactorRow(BaseModel):
    factor_id: str
    label: str
    team_value: Optional[float] = None
    opponent_value: Optional[float] = None
    league_reference: Optional[float] = None
    margin_signal: Optional[float] = None
    note: str


class TeamFocusLever(BaseModel):
    title: str
    summary: str
    impact_label: str
    factor_id: str
    rationale: Optional[str] = None
    coaching_prompt: Optional[str] = None
    projected_impact: Optional[str] = None
    opponent_context: Optional[str] = None


class TeamFocusLeversReport(BaseModel):
    team_abbreviation: str
    team_name: str
    season: str
    factor_rows: List[TeamFactorRow]
    focus_levers: List[TeamFocusLever]


class TeamUpcomingGameSummary(BaseModel):
    game_id: str
    game_date: Optional[date] = None
    opponent_abbreviation: Optional[str] = None
    opponent_name: Optional[str] = None
    is_home: bool
    status: str


class TeamAvailabilityPlayer(BaseModel):
    player_id: int
    player_name: str
    position: str
    jersey: str
    headshot_url: str
    injury_status: Optional[str] = None
    injury_type: Optional[str] = None
    detail: Optional[str] = None
    comment: Optional[str] = None
    return_date: Optional[date] = None
    pts_pg: Optional[float] = None
    bpm: Optional[float] = None
    impact_label: str


class TeamAvailabilityResponse(BaseModel):
    team_id: int
    abbreviation: str
    name: str
    season: str
    report_date: Optional[date] = None
    overall_status: str
    summary: str
    available_count: int = 0
    unavailable_count: int = 0
    questionable_count: int = 0
    probable_count: int = 0
    next_game: Optional[TeamUpcomingGameSummary] = None
    key_absences: List[TeamAvailabilityPlayer]
    unavailable_players: List[TeamAvailabilityPlayer]
    questionable_players: List[TeamAvailabilityPlayer]
    probable_players: List[TeamAvailabilityPlayer]
