from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class ShotChartShot(BaseModel):
    loc_x: int
    loc_y: int
    shot_made: bool
    shot_type: str
    action_type: str
    zone_basic: str
    zone_area: str
    distance: int
    game_id: Optional[str] = None
    game_date: Optional[str] = None
    period: Optional[int] = None
    clock: Optional[str] = None
    minutes_remaining: Optional[int] = None
    seconds_remaining: Optional[int] = None
    shot_value: Optional[int] = None
    shot_event_id: Optional[str] = None
    team_id: Optional[int] = None
    team_abbreviation: Optional[str] = None
    opponent_team_id: Optional[int] = None
    opponent_team_abbreviation: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    score_margin: Optional[int] = None
    event_order_index: Optional[int] = None
    action_number: Optional[int] = None
    linkage_mode: Optional[str] = None


class ShotCompletenessSummary(BaseModel):
    status: str
    total_shots: int
    contextual_shots: int
    linked_shots: int
    exact_linked_shots: int
    derived_linked_shots: int = 0
    completeness_pct: float
    linked_pct: float
    missing_context_fields: List[str] = []


class ShotChartResponse(BaseModel):
    player_id: int
    season: str
    season_type: str
    shots: List[ShotChartShot]
    made: int
    attempted: int
    data_status: str
    last_synced_at: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_start_date: Optional[str] = None
    available_end_date: Optional[str] = None
    available_game_dates: List[str] = []
    completeness_status: str = "missing"
    missing_context_fields: List[str] = []
    linked_event_attempts: int = 0
    exact_event_linked_attempts: int = 0
    derived_event_linked_attempts: int = 0
    completeness: Optional[ShotCompletenessSummary] = None


class ZoneStat(BaseModel):
    zone_basic: str
    zone_area: str
    attempts: int
    made: int
    fg_pct: Optional[float] = None
    pps: Optional[float] = None
    freq: float


class ZoneProfileResponse(BaseModel):
    player_id: int
    season: str
    season_type: str
    total_attempts: int
    zones: List[ZoneStat]
    data_status: str
    last_synced_at: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_start_date: Optional[str] = None
    available_end_date: Optional[str] = None
    available_game_dates: List[str] = []
    completeness_status: str = "missing"
    missing_context_fields: List[str] = []
    linked_event_attempts: int = 0
    exact_event_linked_attempts: int = 0
    derived_event_linked_attempts: int = 0
    completeness: Optional[ShotCompletenessSummary] = None


class TeamDefenseShotChartResponse(BaseModel):
    team_id: int
    team_abbreviation: Optional[str] = None
    team_name: Optional[str] = None
    season: str
    season_type: str
    shots: List[ShotChartShot]
    made: int
    attempted: int
    data_status: str
    last_synced_at: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_start_date: Optional[str] = None
    available_end_date: Optional[str] = None
    available_game_dates: List[str] = []
    completeness_status: str = "missing"
    missing_context_fields: List[str] = []
    linked_event_attempts: int = 0
    exact_event_linked_attempts: int = 0
    derived_event_linked_attempts: int = 0
    completeness: Optional[ShotCompletenessSummary] = None


class TeamDefenseZoneProfileResponse(BaseModel):
    team_id: int
    team_abbreviation: Optional[str] = None
    team_name: Optional[str] = None
    season: str
    season_type: str
    total_attempts: int
    zones: List[ZoneStat]
    data_status: str
    last_synced_at: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    available_start_date: Optional[str] = None
    available_end_date: Optional[str] = None
    available_game_dates: List[str] = []
    completeness_status: str = "missing"
    missing_context_fields: List[str] = []
    linked_event_attempts: int = 0
    exact_event_linked_attempts: int = 0
    derived_event_linked_attempts: int = 0
    completeness: Optional[ShotCompletenessSummary] = None


class ShotCompletenessEntity(BaseModel):
    entity_id: str
    entity_type: str
    data_status: str
    completeness_status: str
    total_shots: int
    contextual_shots: int
    linked_shots: int
    exact_linked_shots: int
    last_synced_at: Optional[str] = None


class ShotCompletenessDomain(BaseModel):
    domain: str
    eligible_count: int
    ready_count: int
    partial_count: int
    legacy_count: int
    missing_count: int
    completeness_pct: float


class ShotCompletenessReportResponse(BaseModel):
    season: str
    season_type: str
    supported_seasons: List[str]
    domains: List[ShotCompletenessDomain]
    rows: List[ShotCompletenessEntity]


class ShotLabSnapshotFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    period_bucket: str = "all"
    result: str = "all"
    shot_value: str = "all"


class ShotLabSnapshotPayload(BaseModel):
    subject_type: str
    subject_id: Optional[int] = None
    compare_subject_id: Optional[int] = None
    team_id: Optional[int] = None
    season: str
    season_type: str
    active_view: str
    route_path: str
    filters: ShotLabSnapshotFilters
    metadata: Dict[str, str] = {}


class ShotLabSnapshotCreateRequest(BaseModel):
    subject_type: str
    subject_id: Optional[int] = None
    compare_subject_id: Optional[int] = None
    team_id: Optional[int] = None
    season: str
    season_type: str
    active_view: str
    route_path: str
    filters: ShotLabSnapshotFilters
    metadata: Dict[str, str] = {}


class ShotLabSnapshotResponse(BaseModel):
    snapshot_id: str
    share_url: str
    created_at: Optional[str] = None
    payload: ShotLabSnapshotPayload
