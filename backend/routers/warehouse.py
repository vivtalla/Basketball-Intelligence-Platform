from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.warehouse import (
    IngestionJobResponse,
    JobRunResponse,
    QueueResponse,
    SourceRunResponse,
    WarehouseGameHealth,
    WarehouseJobSummary,
    WarehouseSeasonHealth,
)
from services.warehouse_service import (
    get_game_health,
    get_job_summary,
    get_season_health,
    list_jobs,
    materialize_game_stats,
    materialize_season_aggregates,
    queue_backfill_season,
    queue_current_season_daily_sync,
    queue_date_sync,
    queue_game_resync,
    queue_player_shot_chart_sync,
    queue_season_shot_charts,
    reset_stale_jobs,
    retry_failed_jobs,
    run_next_job,
    sync_game_boxscore,
    sync_game_pbp,
    sync_schedule,
)

router = APIRouter()


def _job_response(row) -> IngestionJobResponse:
    return IngestionJobResponse(
        id=row.id,
        job_type=row.job_type,
        job_key=row.job_key,
        season=row.season,
        game_id=row.game_id,
        priority=row.priority,
        status=row.status,
        attempt_count=row.attempt_count,
        last_error=row.last_error,
        run_after=row.run_after.isoformat() if row.run_after else None,
        leased_until=row.leased_until.isoformat() if row.leased_until else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
    )


@router.post("/queue/season-backfill", response_model=QueueResponse)
def queue_season_backfill(season: str = Query(...), db: Session = Depends(get_db)):
    jobs = queue_backfill_season(db, season)
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])


@router.post("/queue/date-sync", response_model=QueueResponse)
def queue_day_sync(
    season: str = Query(...),
    date_key: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    jobs = queue_date_sync(db, season, date_key)
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])


@router.post("/queue/game-resync", response_model=QueueResponse)
def queue_single_game(game_id: str = Query(...), season: Optional[str] = Query(None), db: Session = Depends(get_db)):
    jobs = queue_game_resync(db, game_id, season=season)
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])


@router.post("/queue/current-season", response_model=QueueResponse)
def queue_daily_current_season(season: str = Query(...), db: Session = Depends(get_db)):
    jobs = queue_current_season_daily_sync(db, season)
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])


@router.post("/run-next", response_model=JobRunResponse)
def run_one_job(season: Optional[str] = Query(None), db: Session = Depends(get_db)):
    result = run_next_job(db, season=season)
    job_id = result.get("job_id")
    job = None
    if job_id:
        rows = [row for row in list_jobs(db, season=season, limit=100) if row.id == job_id]
        job = rows[0] if rows else None
    response_result = result.get("result")
    if response_result is None and result.get("reason"):
        response_result = {"reason": result["reason"]}
    elif response_result is None:
        response_result = result
    return JobRunResponse(
        status=result["status"],
        job=_job_response(job) if job else None,
        result=response_result,
    )


@router.post("/retry-failed", response_model=QueueResponse)
def retry_failed(season: str = Query(...), db: Session = Depends(get_db)):
    jobs = retry_failed_jobs(db, season)
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])


@router.post("/reset-stale", response_model=QueueResponse)
def reset_stale(season: Optional[str] = Query(None), db: Session = Depends(get_db)):
    jobs = reset_stale_jobs(db, season=season)
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])


@router.post("/sync/schedule")
def sync_schedule_now(
    season: str = Query(...),
    date_key: Optional[str] = Query(None, description="Optional YYYY-MM-DD filter"),
    db: Session = Depends(get_db),
):
    return sync_schedule(db, season, date_key)


@router.post("/sync/game-boxscore")
def sync_game_boxscore_now(game_id: str = Query(...), db: Session = Depends(get_db)):
    return sync_game_boxscore(db, game_id)


@router.post("/sync/game-pbp")
def sync_game_pbp_now(game_id: str = Query(...), db: Session = Depends(get_db)):
    return sync_game_pbp(db, game_id)


@router.post("/materialize/game")
def materialize_game_now(game_id: str = Query(...), db: Session = Depends(get_db)):
    return materialize_game_stats(db, game_id)


@router.post("/materialize/season")
def materialize_season_now(season: str = Query(...), db: Session = Depends(get_db)):
    return materialize_season_aggregates(db, season)


@router.post("/queue/shot-charts", response_model=QueueResponse)
def queue_shot_charts(
    season: str = Query(...),
    season_type: str = Query("Regular Season"),
    player_id: Optional[int] = Query(None),
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    if season_type not in ("Regular Season", "Playoffs"):
        raise HTTPException(status_code=422, detail='season_type must be "Regular Season" or "Playoffs"')
    if player_id is not None:
        jobs = queue_player_shot_chart_sync(
            db,
            player_id=player_id,
            season=season,
            season_type=season_type,
            force=force,
        )
    else:
        jobs = queue_season_shot_charts(
            db,
            season=season,
            season_type=season_type,
            force=force,
        )
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])


@router.get("/health/{season}", response_model=WarehouseSeasonHealth)
def season_health(season: str, db: Session = Depends(get_db)):
    payload = get_season_health(db, season)
    runs = [SourceRunResponse(**row) for row in payload.pop("latest_runs")]
    return WarehouseSeasonHealth(**payload, latest_runs=runs)


@router.get("/games/{game_id}/health", response_model=WarehouseGameHealth)
def game_health(game_id: str, db: Session = Depends(get_db)):
    payload = get_game_health(db, game_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"Warehouse game {game_id} not found")
    return WarehouseGameHealth(**payload)


@router.get("/jobs", response_model=List[IngestionJobResponse])
def jobs(
    status: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return [_job_response(row) for row in list_jobs(db, status=status, season=season, limit=limit)]


@router.get("/jobs/summary", response_model=WarehouseJobSummary)
def jobs_summary(season: Optional[str] = Query(None), db: Session = Depends(get_db)):
    return WarehouseJobSummary(**get_job_summary(db, season=season))
