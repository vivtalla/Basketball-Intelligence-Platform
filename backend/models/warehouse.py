from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IngestionJobResponse(BaseModel):
    id: int
    job_type: str
    job_key: str
    season: Optional[str] = None
    game_id: Optional[str] = None
    priority: int
    status: str
    attempt_count: int
    last_error: Optional[str] = None
    run_after: Optional[str] = None
    leased_until: Optional[str] = None
    completed_at: Optional[str] = None


class SourceRunResponse(BaseModel):
    id: int
    source: str
    job_type: str
    entity_type: str
    entity_id: str
    status: str
    attempt_count: int
    records_written: int
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    run_metadata: Optional[Dict[str, Any]] = None


class WarehouseGameHealth(BaseModel):
    game_id: str
    season: str
    game_date: Optional[str] = None
    status: str
    home_team_abbreviation: Optional[str] = None
    away_team_abbreviation: Optional[str] = None
    has_schedule: bool
    has_final_box_score: bool
    has_pbp_payload: bool
    has_parsed_pbp: bool
    has_materialized_game_stats: bool
    has_materialized_season: bool
    pbp_parse_status: str
    game_player_rows: int = 0
    game_team_rows: int = 0
    pbp_event_rows: int = 0
    raw_payload_types: List[str] = []
    last_box_score_sync_at: Optional[str] = None
    last_pbp_sync_at: Optional[str] = None
    last_materialized_at: Optional[str] = None


class WarehouseSeasonHealth(BaseModel):
    season: str
    total_games: int
    scheduled_games: int
    completed_games: int
    games_with_box_score: int
    games_with_pbp_payload: int
    games_with_parsed_pbp: int
    games_materialized: int
    pending_jobs: int
    running_jobs: int
    failed_jobs: int
    latest_runs: List[SourceRunResponse]


class WarehouseJobTypeSummary(BaseModel):
    job_type: str
    queued: int = 0
    running: int = 0
    complete: int = 0
    failed: int = 0
    skipped: int = 0


class WarehouseRequestThrottleStatus(BaseModel):
    source: str
    available_at: Optional[str] = None
    last_request_at: Optional[str] = None
    seconds_until_available: float = 0.0


class WarehouseJobSummary(BaseModel):
    season: Optional[str] = None
    status_counts: Dict[str, int]
    job_types: List[WarehouseJobTypeSummary]
    oldest_queued_job: Optional[IngestionJobResponse] = None
    stalled_running_jobs: List[IngestionJobResponse]
    global_request_throttle: Optional[WarehouseRequestThrottleStatus] = None


class QueueResponse(BaseModel):
    queued: int
    jobs: List[IngestionJobResponse]


class JobRunResponse(BaseModel):
    status: str
    job: Optional[IngestionJobResponse] = None
    result: Optional[Dict[str, Any]] = None
