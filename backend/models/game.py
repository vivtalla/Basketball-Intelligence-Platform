from typing import Dict, List, Optional

from pydantic import BaseModel


class GameEvent(BaseModel):
    action_number: int
    source_event_id: Optional[str] = None
    order_index: Optional[int] = None
    period: Optional[int] = None
    clock: Optional[str] = None
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    event_type: Optional[str] = None
    action_family: Optional[str] = None
    sub_type: Optional[str] = None
    description: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class GameTimelinePoint(BaseModel):
    action_number: int
    period: Optional[int] = None
    clock: Optional[str] = None
    home_score: int
    away_score: int
    scoring_team_id: Optional[int] = None
    scoring_team_abbreviation: Optional[str] = None
    description: Optional[str] = None


class GamePlayerSummary(BaseModel):
    player_id: int
    player_name: str
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    min: Optional[float] = None
    plus_minus: Optional[int] = None


class WinProbPoint(BaseModel):
    seconds_elapsed: int       # 0 at tip, 2880 at end of regulation
    score_home: int
    score_away: int
    wp_home: float             # 0.0..1.0
    event: Optional[str] = None  # swing label, e.g. "+8 RUN"


class LeadPoint(BaseModel):
    minute: int                # 0..48 (or higher for OT)
    home_lead: int             # positive = home leading, negative = away leading


class GameDetailResponse(BaseModel):
    game_id: str
    season: str
    game_date: Optional[str] = None
    matchup: Optional[str] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_team_name: Optional[str] = None
    home_team_abbreviation: Optional[str] = None
    away_team_name: Optional[str] = None
    away_team_abbreviation: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    data_status: str = "missing"
    completeness_status: str = "missing"
    canonical_source: Optional[str] = None
    last_synced_at: Optional[str] = None
    timeline: List[GameTimelinePoint]
    top_players: List[GamePlayerSummary]
    events: List[GameEvent]
    win_probability: Optional[List[WinProbPoint]] = None
    lead_tracker: Optional[List[LeadPoint]] = None
    possession_diary: Optional[List["PossessionEntry"]] = None
    player_quarter_impact: Optional[List["PlayerQuarterImpact"]] = None
    series_odds_history: Optional[List["SeriesOddsPoint"]] = None


class GameTeamBoxScore(BaseModel):
    team_id: int
    team_abbreviation: Optional[str] = None
    is_home: bool
    won: Optional[bool] = None
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    fgm: int = 0
    fga: int = 0
    fg_pct: Optional[float] = None
    fg3m: int = 0
    fg3a: int = 0
    fg3_pct: Optional[float] = None
    ftm: int = 0
    fta: int = 0
    ft_pct: Optional[float] = None
    oreb: int = 0
    dreb: int = 0
    pf: int = 0
    plus_minus: Optional[float] = None


class GamePlayerBoxScore(BaseModel):
    player_id: int
    player_name: str
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    is_starter: bool
    wl: Optional[str] = None
    min: Optional[float] = None
    pts: int = 0
    reb: int = 0
    ast: int = 0
    stl: int = 0
    blk: int = 0
    tov: int = 0
    fgm: int = 0
    fga: int = 0
    fg_pct: Optional[float] = None
    fg3m: int = 0
    fg3a: int = 0
    fg3_pct: Optional[float] = None
    ftm: int = 0
    fta: int = 0
    ft_pct: Optional[float] = None
    oreb: int = 0
    dreb: int = 0
    pf: int = 0
    plus_minus: Optional[float] = None


class GameSummaryResponse(BaseModel):
    game_id: str
    season: str
    game_date: Optional[str] = None
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None
    home_team_abbreviation: Optional[str] = None
    away_team_abbreviation: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    materialized: bool
    home_team_stats: Optional[GameTeamBoxScore] = None
    away_team_stats: Optional[GameTeamBoxScore] = None
    players: List[GamePlayerBoxScore]


class GameVisualizationElement(BaseModel):
    kind: str
    label: Optional[str] = None
    exactness: str
    linkage_mode: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    shot_made: Optional[bool] = None
    shot_value: Optional[int] = None
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    event_type: Optional[str] = None


class GameVisualizationStep(BaseModel):
    action_number: int
    order_index: int
    source_event_id: Optional[str] = None
    period: Optional[int] = None
    clock: Optional[str] = None
    event_type: Optional[str] = None
    action_family: Optional[str] = None
    sub_type: Optional[str] = None
    description: Optional[str] = None
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    exact_shot_match: bool = False
    linkage_quality: str = "timeline"
    sequence_role: Optional[str] = None
    sequence_offset: Optional[int] = None
    elements: List[GameVisualizationElement]


class GameVisualizationResponse(BaseModel):
    game_id: str
    season: str
    shot_event_id: Optional[str] = None
    source: Optional[str] = None
    selected_player_id: Optional[int] = None
    selected_period: Optional[int] = None
    selected_event_type: Optional[str] = None
    selected_query: Optional[str] = None
    data_status: str = "missing"
    completeness_status: str = "missing"
    canonical_source: Optional[str] = None
    last_synced_at: Optional[str] = None
    exact_shot_match: bool = False
    linkage_quality: str = "timeline"
    highlighted_event_id: Optional[str] = None
    highlighted_action_number: Optional[int] = None
    focus_event_id: Optional[str] = None
    focus_action_number: Optional[int] = None
    focus_window: int = 1
    focus_steps: List[GameVisualizationStep] = []
    source_context: Optional[Dict[str, str]] = None
    steps: List[GameVisualizationStep]


# ---------------------------------------------------------------------------
# Sprint 77 — Possession Diary + Per-Quarter +/- (Engineer EA2)
# ---------------------------------------------------------------------------


class PossessionEntry(BaseModel):
    """One scoring or impact-tagged possession from a game.

    Returned as part of the top 24 most lead-impactful possessions for a game.
    `impact_tag` is one of: "shot", "defense", "turnover", "transition", "clutch".
    """

    quarter: int
    time_remaining: str  # "MM:SS" of game clock at start of possession
    offense_team_abbr: str
    primary_action_type: str
    primary_player_name: str
    points_scored: int
    impact_tag: str
    lead_swing: int


class PlayerQuarterImpact(BaseModel):
    """Per-player per-quarter on-court +/- and minutes.

    Quarters 1-4 are regulation; 5+ are overtime.
    """

    player_id: int
    player_name: str
    team_abbreviation: str
    quarter: int
    plus_minus: int
    minutes: float


# ---------------------------------------------------------------------------
# Sprint 77 — Series odds history (Engineer EA3)
# ---------------------------------------------------------------------------


class SeriesOddsPoint(BaseModel):
    """Post-game series-odds snapshot for a single completed playoff series game.

    For each completed game in a series, ``top_seed_post_game_odds`` is the
    simulator's estimate of the top-seed's chance of winning the series given
    only the games up to and including this one. ``swing_pp`` is the change
    relative to the previous game's snapshot (or relative to the pre-series
    prior for Game 1).
    """

    game_num: int
    date: str                        # ISO date of game
    winner_team_abbr: str
    top_seed_post_game_odds: float   # 0.0..1.0
    swing_pp: float                  # change in pp from previous snapshot


GameDetailResponse.model_rebuild()
