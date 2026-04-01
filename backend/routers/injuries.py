"""Injuries router: current injury report and per-player injury history."""
from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, PlayerInjury
from services.sync_service import sync_injuries

router = APIRouter()


class InjuryEntry(BaseModel):
    player_id: int
    player_name: str
    report_date: date
    return_date: Optional[date]
    injury_type: Optional[str]
    injury_status: Optional[str]
    detail: Optional[str]
    comment: Optional[str]
    season: Optional[str]

    class Config:
        from_attributes = True


class InjuryReportResponse(BaseModel):
    report_date: date
    count: int
    injuries: List[InjuryEntry]


@router.get("/current", response_model=InjuryReportResponse)
def get_current_injuries(
    season: str = Query("2024-25", description="Season string e.g. 2024-25"),
    db: Session = Depends(get_db),
):
    """Return the most recent injury report for every currently injured player."""
    # Latest report_date in the table
    latest = (
        db.query(PlayerInjury.report_date)
        .filter(PlayerInjury.season == season)
        .order_by(PlayerInjury.report_date.desc())
        .first()
    )
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No injury data found. Run sync_injuries to populate.",
        )
    report_date = latest[0]

    rows = (
        db.query(PlayerInjury, Player.full_name)
        .join(Player, Player.id == PlayerInjury.player_id)
        .filter(PlayerInjury.report_date == report_date)
        .order_by(PlayerInjury.injury_status, Player.full_name)
        .all()
    )

    injuries = [
        InjuryEntry(
            player_id=inj.player_id,
            player_name=name,
            report_date=inj.report_date,
            return_date=inj.return_date,
            injury_type=inj.injury_type,
            injury_status=inj.injury_status,
            detail=inj.detail,
            comment=inj.comment,
            season=inj.season,
        )
        for inj, name in rows
    ]
    return InjuryReportResponse(
        report_date=report_date,
        count=len(injuries),
        injuries=injuries,
    )


@router.get("/player/{player_id}", response_model=List[InjuryEntry])
def get_player_injuries(
    player_id: int,
    season: Optional[str] = Query(None, description="Filter by season e.g. 2024-25"),
    db: Session = Depends(get_db),
):
    """Return injury history for a single player."""
    q = (
        db.query(PlayerInjury, Player.full_name)
        .join(Player, Player.id == PlayerInjury.player_id)
        .filter(PlayerInjury.player_id == player_id)
    )
    if season:
        q = q.filter(PlayerInjury.season == season)
    rows = q.order_by(PlayerInjury.report_date.desc()).all()

    return [
        InjuryEntry(
            player_id=inj.player_id,
            player_name=name,
            report_date=inj.report_date,
            return_date=inj.return_date,
            injury_type=inj.injury_type,
            injury_status=inj.injury_status,
            detail=inj.detail,
            comment=inj.comment,
            season=inj.season,
        )
        for inj, name in rows
    ]


@router.post("/sync")
def trigger_injury_sync(
    season: str = Query("2024-25", description="Season to tag injury records with"),
    db: Session = Depends(get_db),
):
    """Fetch the current CDN injury report and persist it. Idempotent."""
    try:
        summary = sync_injuries(db, season)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Injury sync failed: {exc}")
    return {"status": "ok", **summary}
