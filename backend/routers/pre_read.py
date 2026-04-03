from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.pre_read import (
    PreReadDeckResponse,
    PreReadSnapshotCreateRequest,
    PreReadSnapshotListResponse,
    PreReadSnapshotResponse,
)
from models.scouting import PlayTypeScoutingReportResponse
from routers.scouting import build_play_type_scouting_report
from services.pre_read_service import build_pre_read_deck
from services.pre_read_snapshot_service import (
    create_pre_read_snapshot,
    get_pre_read_snapshot,
    list_pre_read_snapshots,
)

router = APIRouter()


@router.get("", response_model=PreReadDeckResponse)
def get_pre_read(
    team: Optional[str] = Query(None),
    opponent: Optional[str] = Query(None),
    season: str = Query("2024-25"),
    snapshot_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if snapshot_id:
        return get_pre_read_snapshot(db=db, snapshot_id=snapshot_id).deck
    if not team or not opponent:
        raise HTTPException(status_code=422, detail="team and opponent are required when snapshot_id is not provided.")
    return build_pre_read_deck(db=db, team=team, opponent=opponent, season=season)


@router.post("/snapshots", response_model=PreReadSnapshotResponse)
def post_pre_read_snapshot(
    payload: PreReadSnapshotCreateRequest,
    db: Session = Depends(get_db),
):
    return create_pre_read_snapshot(db=db, payload=payload)


@router.get("/snapshots", response_model=PreReadSnapshotListResponse)
def get_pre_read_snapshots(
    team: Optional[str] = Query(None),
    opponent: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return list_pre_read_snapshots(db=db, team=team, opponent=opponent, season=season, limit=limit)


@router.get("/snapshots/{snapshot_id}", response_model=PreReadSnapshotResponse)
def get_pre_read_snapshot_route(
    snapshot_id: str,
    db: Session = Depends(get_db),
):
    return get_pre_read_snapshot(db=db, snapshot_id=snapshot_id)


@router.get("/scouting", response_model=PlayTypeScoutingReportResponse)
def get_pre_read_scouting_report(
    team: str = Query(...),
    opponent: str = Query(...),
    season: str = Query("2025-26"),
    window: int = Query(10, ge=3, le=20),
    db: Session = Depends(get_db),
):
    return build_play_type_scouting_report(
        db=db,
        team=team,
        opponent=opponent,
        season=season,
        window=window,
    )
