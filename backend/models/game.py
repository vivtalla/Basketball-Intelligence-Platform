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
