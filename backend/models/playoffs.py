"""Pydantic schemas for the playoff API surface (Sprint 73).

Covers the bracket overview, per-series detail, today's slate, and the
series simulator response.
"""
from __future__ import annotations

from datetime import date as _date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from models.methodology import AnalysisMetadata


PlayoffSeriesStatus = Literal["scheduled", "active", "closed"]


class PlayoffSeriesGame(BaseModel):
    game_id: str
    game_date: Optional[_date] = None
    home_team_id: Optional[int] = None
    home_team_abbr: Optional[str] = None
    away_team_id: Optional[int] = None
    away_team_abbr: Optional[str] = None
    home_pts: Optional[int] = None
    away_pts: Optional[int] = None
    winner_team_id: Optional[int] = None
    series_game_num: Optional[int] = None


class PlayoffSeriesResponse(BaseModel):
    season: str
    round: int
    series_id: str
    top_seed_team_id: Optional[int] = None
    bottom_seed_team_id: Optional[int] = None
    top_seed_team_abbr: Optional[str] = None
    bottom_seed_team_abbr: Optional[str] = None
    top_seed: int
    bottom_seed: int
    top_wins: int
    bottom_wins: int
    status: PlayoffSeriesStatus
    winner_team_id: Optional[int] = None
    games: List[PlayoffSeriesGame] = []


class PlayoffBracketResponse(BaseModel):
    season: str
    east: List[PlayoffSeriesResponse] = []
    west: List[PlayoffSeriesResponse] = []
    finals: Optional[PlayoffSeriesResponse] = None


class PlayoffSeriesGameWithMatchup(PlayoffSeriesGame):
    """A playoff game annotated with the series context it belongs to."""
    series_id: Optional[str] = None
    season: Optional[str] = None
    round: Optional[int] = None
    top_seed_team_abbr: Optional[str] = None
    bottom_seed_team_abbr: Optional[str] = None
    top_wins: Optional[int] = None
    bottom_wins: Optional[int] = None
    status: Optional[PlayoffSeriesStatus] = None


class PlayoffTodayResponse(BaseModel):
    date: _date
    games: List[PlayoffSeriesGameWithMatchup] = []


class SeriesSimulationCurrentState(BaseModel):
    top_seed_team_abbr: Optional[str] = None
    bottom_seed_team_abbr: Optional[str] = None
    top_wins: int
    bottom_wins: int
    games_played: int
    status: PlayoffSeriesStatus


class SeriesProjectionEntry(BaseModel):
    game_num: int
    home_team_abbr: Optional[str] = None
    away_team_abbr: Optional[str] = None
    home_win_prob: float


class SeriesSimulationResponse(BaseModel):
    series_id: str
    current_state: SeriesSimulationCurrentState
    projection: List[SeriesProjectionEntry] = []
    top_seed_series_win_prob: float = 0.0
    bottom_seed_series_win_prob: float = 0.0
    trials: int = 0


class PlayoffSeriesTeamRef(BaseModel):
    team_id: Optional[int] = None
    abbreviation: Optional[str] = None
    seed: Optional[int] = None
    wins: int = 0


class PlayoffGameMargin(BaseModel):
    game_num: Optional[int] = None
    winner_team_abbr: Optional[str] = None
    margin: Optional[int] = None


class PlayoffSeriesPulse(BaseModel):
    summary: str
    next_game_number: Optional[int] = None
    leader_team_abbr: Optional[str] = None
    trailing_team_abbr: Optional[str] = None
    is_elimination_game: bool = False
    is_swing_game: bool = False
    completed_games: int = 0
    margin_by_game: List[PlayoffGameMargin] = Field(default_factory=list)
    last_game_note: Optional[str] = None


class PlayoffSeriesDataCoverage(BaseModel):
    completed_games: int = 0
    playoff_team_stats: bool = False
    regular_team_baselines: bool = False
    playoff_player_stats: bool = False
    playoff_lineups: bool = False
    shot_profile_splits: bool = False
    warnings: List[str] = Field(default_factory=list)


class PlayoffMetricEdge(BaseModel):
    key: str
    label: str
    unit: str = "number"
    higher_is_better: Optional[bool] = True
    top_value: Optional[float] = None
    bottom_value: Optional[float] = None
    top_regular_value: Optional[float] = None
    bottom_regular_value: Optional[float] = None
    top_delta_vs_regular: Optional[float] = None
    bottom_delta_vs_regular: Optional[float] = None
    edge_team_abbr: Optional[str] = None
    edge_amount: Optional[float] = None


class PlayoffStarBurdenEntry(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: str
    position: Optional[str] = None
    position_bucket: Optional[str] = None
    gp: int = 0
    min_pg: Optional[float] = None
    usg_pct: Optional[float] = None
    pts_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    bpm: Optional[float] = None
    share_team_points: Optional[float] = None
    share_team_usage: Optional[float] = None


class PlayoffShotDietEntry(BaseModel):
    team_abbreviation: str
    rim_frequency: Optional[float] = None
    paint_frequency: Optional[float] = None
    three_point_frequency: Optional[float] = None
    corner_three_frequency: Optional[float] = None
    above_break_three_frequency: Optional[float] = None
    ftr: Optional[float] = None
    par3: Optional[float] = None
    assisted_fg_rate: Optional[float] = None
    notes: List[str] = Field(default_factory=list)


class PlayoffLineupEntry(BaseModel):
    team_abbreviation: Optional[str] = None
    lineup_key: str
    player_names: List[str] = Field(default_factory=list)
    minutes: Optional[float] = None
    possessions: Optional[int] = None
    net_rating: Optional[float] = None
    ortg: Optional[float] = None
    drtg: Optional[float] = None
    label: str


class PlayoffTacticalEdge(BaseModel):
    edge_type: str
    title: str
    team_abbreviation: Optional[str] = None
    summary: str
    metric_key: Optional[str] = None
    impact_score: Optional[float] = None


class PlayoffAdjustmentSignal(BaseModel):
    title: str
    summary: str
    team_abbreviation: Optional[str] = None
    confidence: Literal["high", "medium", "low"] = "medium"


class PlayoffSeriesIntelligenceResponse(BaseModel):
    methodology_version: str = "playoff_series_intelligence_v1"
    series_id: str
    season: str
    round: int
    top_team: PlayoffSeriesTeamRef
    bottom_team: PlayoffSeriesTeamRef
    pulse: PlayoffSeriesPulse
    data_coverage: PlayoffSeriesDataCoverage
    four_factors: List[PlayoffMetricEdge] = Field(default_factory=list)
    star_burden: List[PlayoffStarBurdenEntry] = Field(default_factory=list)
    shot_diet: List[PlayoffShotDietEntry] = Field(default_factory=list)
    best_lineups: List[PlayoffLineupEntry] = Field(default_factory=list)
    worst_lineups: List[PlayoffLineupEntry] = Field(default_factory=list)
    tactical_edges: List[PlayoffTacticalEdge] = Field(default_factory=list)
    adjustment_signals: List[PlayoffAdjustmentSignal] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    analysis_metadata: Optional[AnalysisMetadata] = None
