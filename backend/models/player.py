from typing import List, Optional

from pydantic import BaseModel


class PlayerSearchResult(BaseModel):
    id: int
    full_name: str
    is_active: bool


class PlayerProfile(BaseModel):
    id: int
    full_name: str
    first_name: str
    last_name: str
    team_name: str
    team_abbreviation: str
    team_id: Optional[int] = None
    jersey: str
    position: str
    height: str
    weight: str
    birth_date: str
    country: str
    school: Optional[str] = None
    draft_year: Optional[str] = None
    draft_round: Optional[str] = None
    draft_number: Optional[str] = None
    from_year: Optional[int] = None
    to_year: Optional[int] = None
    headshot_url: str


class PlayerTrendForm(BaseModel):
    games: int = 0
    avg_minutes: Optional[float] = None
    avg_points: Optional[float] = None
    avg_rebounds: Optional[float] = None
    avg_assists: Optional[float] = None
    avg_fg_pct: Optional[float] = None
    avg_fg3_pct: Optional[float] = None
    avg_plus_minus: Optional[float] = None


class PlayerTrendSignals(BaseModel):
    minutes_delta: Optional[float] = None
    points_delta: Optional[float] = None
    efficiency_delta: Optional[float] = None
    starts_last_10: int = 0
    bench_games_last_10: int = 0
    games_30_plus_last_10: int = 0
    games_under_20_last_10: int = 0
    minute_volatility: Optional[float] = None


class PlayerTrendImpactSnapshot(BaseModel):
    pbp_coverage_status: str
    on_off_net: Optional[float] = None
    on_minutes: Optional[float] = None
    bpm: Optional[float] = None
    per: Optional[float] = None
    pts_pg: Optional[float] = None
    ts_pct: Optional[float] = None


class PlayerTrendGame(BaseModel):
    game_id: str
    game_date: Optional[str] = None
    matchup: Optional[str] = None
    result: Optional[str] = None
    minutes: Optional[float] = None
    points: Optional[int] = None
    plus_minus: Optional[int] = None
    is_starter: bool = False
    trend_note: str


class PlayerTrendReport(BaseModel):
    player_id: int
    player_name: str
    team_abbreviation: Optional[str] = None
    season: str
    status: str
    window_games: int = 0
    role_status: str
    recent_form: PlayerTrendForm
    season_baseline: PlayerTrendForm
    trust_signals: PlayerTrendSignals
    impact_snapshot: PlayerTrendImpactSnapshot
    recommended_games: List[PlayerTrendGame]
