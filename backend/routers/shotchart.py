from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import PlayerShotChart
from models.warehouse import IngestionJobResponse, QueueResponse
from models.shotchart import ShotChartResponse, ShotChartShot, ZoneProfileResponse, ZoneStat
from services.warehouse_service import queue_player_shot_chart_sync

router = APIRouter()

# Zone point values for PPS calculation
_ZONE_POINTS = {
    "Restricted Area": 2,
    "In The Paint (Non-RA)": 2,
    "Mid-Range": 2,
    "Left Corner 3": 3,
    "Right Corner 3": 3,
    "Above the Break 3": 3,
    "Backcourt": 3,
}

_PERIOD_BUCKETS = {"all", "q1", "q2", "q3", "q4", "ot"}
_SHOT_RESULTS = {"all", "made", "missed"}
_SHOT_VALUES = {"all", "2pt", "3pt"}


def _data_status(cached: Optional[PlayerShotChart], now: datetime) -> str:
    if not cached:
        return "missing"
    if not cached.shot_count:
        return "missing"
    if cached.expires_at and cached.expires_at > now:
        return "ready"
    return "stale"


def _last_synced_at(cached: Optional[PlayerShotChart]) -> Optional[str]:
    return cached.fetched_at.isoformat() if cached and cached.fetched_at else None


def _parse_filter_date(raw_value: Optional[str], field_name: str) -> Optional[date]:
    if raw_value is None:
        return None
    if not isinstance(raw_value, str):
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} must be YYYY-MM-DD") from exc


def _parse_period_bucket(period_bucket: str) -> str:
    if not isinstance(period_bucket, str):
        return "all"
    value = (period_bucket or "all").strip().lower()
    if value not in _PERIOD_BUCKETS:
        raise HTTPException(status_code=422, detail='period_bucket must be one of "all", "q1", "q2", "q3", "q4", or "ot"')
    return value


def _parse_shot_result(result: str) -> str:
    if not isinstance(result, str):
        return "all"
    value = (result or "all").strip().lower()
    if value not in _SHOT_RESULTS:
        raise HTTPException(status_code=422, detail='result must be one of "all", "made", or "missed"')
    return value


def _parse_shot_value(shot_value: str) -> str:
    if not isinstance(shot_value, str):
        return "all"
    value = (shot_value or "all").strip().lower()
    if value not in _SHOT_VALUES:
        raise HTTPException(status_code=422, detail='shot_value must be one of "all", "2pt", or "3pt"')
    return value


def _shot_date(raw_shot: dict) -> Optional[date]:
    raw_value = raw_shot.get("game_date")
    if not raw_value:
        return None
    try:
        return date.fromisoformat(str(raw_value)[:10])
    except ValueError:
        return None


def _shot_period(raw_shot: dict) -> Optional[int]:
    raw_value = raw_shot.get("period")
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _matches_period_bucket(raw_shot: dict, period_bucket: str) -> bool:
    if period_bucket == "all":
        return True
    period = _shot_period(raw_shot)
    if period is None:
        return False
    if period_bucket == "ot":
        return period > 4
    expected = int(period_bucket[1])
    return period == expected


def _matches_shot_result(raw_shot: dict, result: str) -> bool:
    if result == "all":
        return True
    shot_made = bool(raw_shot.get("shot_made"))
    return shot_made if result == "made" else not shot_made


def _matches_shot_value(raw_shot: dict, shot_value: str) -> bool:
    if shot_value == "all":
        return True
    raw_value = raw_shot.get("shot_value")
    if raw_value is None:
        shot_type = str(raw_shot.get("shot_type") or "").upper()
        raw_value = 3 if "3PT" in shot_type else 2
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return False
    return parsed == (3 if shot_value == "3pt" else 2)


def _available_game_dates(raw_shots: list[dict]) -> list[str]:
    dates = sorted(
        {
            parsed.isoformat()
            for shot in raw_shots
            if (parsed := _shot_date(shot)) is not None
        }
    )
    return dates


def _filter_shots(
    raw_shots: List[dict],
    start_date: Optional[date],
    end_date: Optional[date],
) -> List[dict]:
    return _filter_shots_with_context(raw_shots, start_date, end_date, "all", "all", "all")


def _filter_shots_with_context(
    raw_shots: List[dict],
    start_date: Optional[date],
    end_date: Optional[date],
    period_bucket: str,
    result: str,
    shot_value: str,
) -> List[dict]:
    if (
        start_date is None
        and end_date is None
        and period_bucket == "all"
        and result == "all"
        and shot_value == "all"
    ):
        return list(raw_shots)

    filtered: List[dict] = []
    for shot in raw_shots:
        if start_date is not None or end_date is not None:
            shot_date = _shot_date(shot)
            if shot_date is None:
                continue
            if start_date is not None and shot_date < start_date:
                continue
            if end_date is not None and shot_date > end_date:
                continue
        if not _matches_period_bucket(shot, period_bucket):
            continue
        if not _matches_shot_result(shot, result):
            continue
        if not _matches_shot_value(shot, shot_value):
            continue
        filtered.append(shot)
    return filtered


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


def _build_response(
    player_id: int,
    season: str,
    season_type: str,
    raw_shots: List[dict],
    available_shots: List[dict],
    start_date: Optional[date],
    end_date: Optional[date],
    data_status: str,
    last_synced_at: Optional[str],
) -> ShotChartResponse:
    shots = [ShotChartShot(**s) for s in raw_shots]
    made = sum(1 for s in shots if s.shot_made)
    available_dates = _available_game_dates(available_shots)
    return ShotChartResponse(
        player_id=player_id,
        season=season,
        season_type=season_type,
        shots=shots,
        made=made,
        attempted=len(shots),
        data_status=data_status,
        last_synced_at=last_synced_at,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
        available_start_date=available_dates[0] if available_dates else None,
        available_end_date=available_dates[-1] if available_dates else None,
        available_game_dates=available_dates,
    )


@router.get("/{player_id}/zones", response_model=ZoneProfileResponse)
def player_shot_zones(
    player_id: int,
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    season_type: str = Query("Regular Season", description='"Regular Season" or "Playoffs"'),
    start_date: Optional[str] = Query(None, description='Optional start date, e.g. "2025-01-01"'),
    end_date: Optional[str] = Query(None, description='Optional end date, e.g. "2025-02-01"'),
    period_bucket: str = Query("all", description='"all", "q1", "q2", "q3", "q4", or "ot"'),
    result: str = Query("all", description='"all", "made", or "missed"'),
    shot_value: str = Query("all", description='"all", "2pt", or "3pt"'),
    db: Session = Depends(get_db),
):
    """Return zone-aggregated shot efficiency for a player from cached shot data.

    Reads only from the player_shot_charts DB cache — no nba_api call.
    Returns total_attempts=0 and zones=[] if no cached data exists.
    """
    if season_type not in ("Regular Season", "Playoffs"):
        raise HTTPException(status_code=422, detail='season_type must be "Regular Season" or "Playoffs"')
    parsed_start_date = _parse_filter_date(start_date, "start_date")
    parsed_end_date = _parse_filter_date(end_date, "end_date")
    parsed_period_bucket = _parse_period_bucket(period_bucket)
    parsed_result = _parse_shot_result(result)
    parsed_shot_value = _parse_shot_value(shot_value)
    if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")

    now = datetime.utcnow()
    cached = (
        db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.player_id == player_id,
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
        )
        .first()
    )

    raw_shots = (cached.shots or []) if cached else []
    available_dates = _available_game_dates(raw_shots)
    shots = _filter_shots_with_context(
        raw_shots,
        parsed_start_date,
        parsed_end_date,
        parsed_period_bucket,
        parsed_result,
        parsed_shot_value,
    )
    total = len(shots)

    # Aggregate by (zone_basic, zone_area)
    zone_map: dict = {}
    for s in shots:
        key = (s.get("zone_basic", "Unknown"), s.get("zone_area", ""))
        if key not in zone_map:
            zone_map[key] = {"made": 0, "attempted": 0}
        zone_map[key]["attempted"] += 1
        if s.get("shot_made"):
            zone_map[key]["made"] += 1

    zones = []
    for (zone_basic, zone_area), counts in zone_map.items():
        att = counts["attempted"]
        made = counts["made"]
        pts = _ZONE_POINTS.get(zone_basic, 2)
        fg_pct = (made / att) if att >= 5 else None
        pps = round(fg_pct * pts, 4) if fg_pct is not None else None
        zones.append(ZoneStat(
            zone_basic=zone_basic,
            zone_area=zone_area,
            attempts=att,
            made=made,
            fg_pct=round(fg_pct, 4) if fg_pct is not None else None,
            pps=pps,
            freq=round(att / total, 4) if total > 0 else 0.0,
        ))

    zones.sort(key=lambda z: z.freq, reverse=True)

    return ZoneProfileResponse(
        player_id=player_id,
        season=season,
        season_type=season_type,
        total_attempts=total,
        zones=zones,
        data_status=_data_status(cached, now),
        last_synced_at=_last_synced_at(cached),
        start_date=parsed_start_date.isoformat() if parsed_start_date else None,
        end_date=parsed_end_date.isoformat() if parsed_end_date else None,
        available_start_date=available_dates[0] if available_dates else None,
        available_end_date=available_dates[-1] if available_dates else None,
    )


@router.get("/{player_id}", response_model=ShotChartResponse)
def player_shot_chart(
    player_id: int,
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    season_type: str = Query("Regular Season", description='"Regular Season" or "Playoffs"'),
    start_date: Optional[str] = Query(None, description='Optional start date, e.g. "2025-01-01"'),
    end_date: Optional[str] = Query(None, description='Optional end date, e.g. "2025-02-01"'),
    period_bucket: str = Query("all", description='"all", "q1", "q2", "q3", "q4", or "ot"'),
    result: str = Query("all", description='"all", "made", or "missed"'),
    shot_value: str = Query("all", description='"all", "2pt", or "3pt"'),
    db: Session = Depends(get_db),
):
    if season_type not in ("Regular Season", "Playoffs"):
        raise HTTPException(status_code=422, detail='season_type must be "Regular Season" or "Playoffs"')
    parsed_start_date = _parse_filter_date(start_date, "start_date")
    parsed_end_date = _parse_filter_date(end_date, "end_date")
    parsed_period_bucket = _parse_period_bucket(period_bucket)
    parsed_result = _parse_shot_result(result)
    parsed_shot_value = _parse_shot_value(shot_value)
    if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")

    now = datetime.utcnow()

    # --- DB cache check ---
    cached = (
        db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.player_id == player_id,
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
        )
        .first()
    )
    if cached:
        filtered_shots = _filter_shots_with_context(
            cached.shots or [],
            parsed_start_date,
            parsed_end_date,
            parsed_period_bucket,
            parsed_result,
            parsed_shot_value,
        )
        return _build_response(
            player_id,
            season,
            season_type,
            filtered_shots,
            cached.shots or [],
            parsed_start_date,
            parsed_end_date,
            data_status=_data_status(cached, now),
            last_synced_at=_last_synced_at(cached),
        )

    return _build_response(
        player_id,
        season,
        season_type,
        [],
        [],
        parsed_start_date,
        parsed_end_date,
        data_status="missing",
        last_synced_at=None,
    )


@router.post("/{player_id}/refresh", response_model=QueueResponse)
def refresh_player_shot_chart(
    player_id: int,
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    season_type: str = Query("Regular Season", description='"Regular Season" or "Playoffs"'),
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    if season_type not in ("Regular Season", "Playoffs"):
        raise HTTPException(status_code=422, detail='season_type must be "Regular Season" or "Playoffs"')
    jobs = queue_player_shot_chart_sync(
        db,
        player_id=player_id,
        season=season,
        season_type=season_type,
        force=force,
    )
    db.commit()
    return QueueResponse(queued=len(jobs), jobs=[_job_response(job) for job in jobs])
