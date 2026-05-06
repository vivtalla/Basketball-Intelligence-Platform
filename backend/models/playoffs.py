"""Pydantic schemas for the playoff API surface (Sprint 73).

Covers the bracket overview, per-series detail, today's slate, and the
series simulator response.
"""
from __future__ import annotations

from datetime import date as _date, datetime
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
    top_seed: Optional[int] = None
    bottom_seed: Optional[int] = None
    top_wins: int = 0
    bottom_wins: int = 0
    status: PlayoffSeriesStatus
    winner_team_id: Optional[int] = None
    games: List[PlayoffSeriesGame] = []
    # Sprint 85 — Bracket auto-advancement. When this row is a Round-(N+1)
    # slot waiting on its parents, these point to the upstream series whose
    # winner fills the top/bottom seat. Null for Round 1 series and for any
    # pre-Sprint-85 rows that haven't been re-walked by the bracket builder.
    parent_top_series_id: Optional[str] = None
    parent_bottom_series_id: Optional[str] = None
    # Sprint 86 — Parent series seed + abbreviation context for richer TBD
    # labels in the frontend (e.g. "winner of 1v8 (OKC/PHX)" instead of
    # "winner of R1"). Resolved by the router from the parent PlayoffSeries
    # row. Null when the corresponding parent_*_series_id is null OR when the
    # parent row is not found.
    parent_top_seed: Optional[int] = None
    parent_bottom_seed: Optional[int] = None
    parent_top_team_abbrs: Optional[List[str]] = None
    parent_bottom_team_abbrs: Optional[List[str]] = None


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
    headline_storyline: Optional[str] = None
    # ISO-8601 UTC tipoff for upcoming games (e.g. "2026-04-28T23:00:00Z").
    # Populated from the live CDN scoreboard when the slate is queried for
    # today; null for completed/historical rows where the time has no UI value.
    tipoff_utc: Optional[str] = None
    broadcaster: Optional[str] = None  # e.g. "TNT", "ESPN" — optional, scoreboard-derived


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
    # Sprint 91 — "playoffs" when this season's playoff sample is non-empty,
    # else "regular_season" when the service fell back to RS rows so the
    # series command center has something to show before Game 1 finalizes.
    data_source: Optional[str] = None


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
    # Sprint 91 — same semantics as PlayoffStarBurdenEntry.data_source.
    data_source: Optional[str] = None


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


# ---------------------------------------------------------------------------
# Sprint 77 — Playoff narrative leaders (PPG with trend + grades)
# ---------------------------------------------------------------------------


class PlayoffLeaderEntry(BaseModel):
    rank: int
    player_id: int
    player_name: str
    team_abbreviation: str
    line: str  # e.g., "31.4 PPG · 7.2 AST · 58.4 TS%"
    trend: str  # "▲" | "→" | "▼"
    recent_games_grade: List[int] = Field(default_factory=list)  # length 5, each 1-5
    impact_score: float = 0.0  # CourtVue composite — see playoff_leaders_service._impact_score


class PlayoffLeadersResponse(BaseModel):
    season: str
    leaders: List[PlayoffLeaderEntry] = Field(default_factory=list)


class PlayoffStoryTile(BaseModel):
    """One tile in the broadsheet Story Rail.

    Auto-generated from platform stats — `headline` and `subhead` are derived
    from current playoff data, `href` deep-links to an internal route
    (typically /players/{id}). Byline is always "CourtVue Numbers Desk" to
    make it explicit these tiles are computed, not editorial.
    """
    kicker: str          # e.g. "Heat Check", "Efficiency Desk", "X-Factor"
    headline: str        # the data-driven hook in serif prose
    subhead: Optional[str] = None  # supporting one-liner
    byline: str = "CourtVue Numbers Desk"
    href: str            # internal route only — never an external URL
    read_time: Optional[str] = None  # short fixture, e.g. "Updated tonight"


class PlayoffStoryRailResponse(BaseModel):
    season: str
    tiles: List[PlayoffStoryTile] = Field(default_factory=list)
    data_as_of: Optional[_date] = None
    computed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Sprint 85 — Per-series detail page (per-team, per-game player stat lines)
# ---------------------------------------------------------------------------


class SeriesPlayerGameLine(BaseModel):
    """One player's stat line for one game in a playoff series.

    Counting stats are integer per-game totals as recorded in
    ``PlayerGameLog``. ``min`` is float because ``PlayerGameLog.min`` is
    stored as a float minute total. For the synthetic ``series_totals`` row
    that aggregates a player's full series, ``series_game_num`` is set to 0
    (sentinel meaning "not a real game") and ``min`` is the minutes summed
    across the series.
    """

    game_id: str
    series_game_num: int
    min: float = 0.0
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    fgm: int = 0
    fga: int = 0
    fg3m: int = 0
    fg3a: int = 0
    ftm: int = 0
    fta: int = 0
    plus_minus: int = 0


class SeriesPlayerLogs(BaseModel):
    """All of one player's per-game stat lines in one series, plus totals."""

    player_id: int
    player_name: str
    team_id: int
    team_abbreviation: str
    headshot_url: Optional[str] = None
    games: List[SeriesPlayerGameLine] = Field(default_factory=list)
    series_totals: SeriesPlayerGameLine


class PlayoffSeriesPlayerLogsResponse(BaseModel):
    """Per-team player logs for a single playoff series.

    Players in each team list are sorted by total minutes played in the
    series (descending) — i.e. the rotation order as actually used.
    """

    series_id: str
    top_seed: List[SeriesPlayerLogs] = Field(default_factory=list)
    bottom_seed: List[SeriesPlayerLogs] = Field(default_factory=list)
