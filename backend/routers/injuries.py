"""Injuries router: current injury report and per-player injury history."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import InjurySyncUnresolved, Player, PlayerInjury, Team
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


class InjurySyncUnresolvedEntry(BaseModel):
    id: int
    season: str
    report_date: date
    team_abbreviation: str
    team_name: str
    player_name: str
    injury_status: str
    injury_type: str
    detail: str
    source: str
    source_url: Optional[str]
    normalized_lookup_key: str

    class Config:
        from_attributes = True


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
        .filter(
            PlayerInjury.report_date == report_date,
            PlayerInjury.season == season,
        )
        .order_by(PlayerInjury.injury_status, Player.full_name)
        .all()
    )

    active_rows = [
        (inj, name)
        for inj, name in rows
        if (inj.injury_status or "").strip().lower() != "available"
    ]

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
        for inj, name in active_rows
    ]
    return InjuryReportResponse(
        report_date=report_date,
        count=len(injuries),
        injuries=injuries,
    )


@router.get("/unresolved", response_model=List[InjurySyncUnresolvedEntry])
def get_unresolved_injuries(
    season: str = Query("2024-25", description="Season string e.g. 2024-25"),
    report_date: Optional[date] = Query(None, description="Optional report date filter"),
    db: Session = Depends(get_db),
):
    """Return unresolved injury sync rows for manual review."""
    query = db.query(InjurySyncUnresolved).filter(InjurySyncUnresolved.season == season)
    if report_date:
        query = query.filter(InjurySyncUnresolved.report_date == report_date)
    rows = (
        query.order_by(
            InjurySyncUnresolved.report_date.desc(),
            InjurySyncUnresolved.team_abbreviation.asc(),
            InjurySyncUnresolved.player_name.asc(),
        )
        .all()
    )
    return [InjurySyncUnresolvedEntry.model_validate(row) for row in rows]


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


class ResolveUnresolvedRequest(BaseModel):
    player_id: int


@router.post("/unresolved/{row_id}/resolve")
def resolve_unresolved_injury(
    row_id: int,
    body: ResolveUnresolvedRequest,
    db: Session = Depends(get_db),
):
    """Manually match an unresolved injury row to a player and upsert the PlayerInjury record."""
    unresolved = db.query(InjurySyncUnresolved).filter(InjurySyncUnresolved.id == row_id).first()
    if not unresolved:
        raise HTTPException(status_code=404, detail="Unresolved row {0} not found.".format(row_id))

    player = db.query(Player).filter(Player.id == body.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player {0} not found.".format(body.player_id))

    team_id: Optional[int] = None
    if unresolved.team_abbreviation:
        team = db.query(Team).filter(Team.abbreviation == unresolved.team_abbreviation).first()
        if team:
            team_id = team.id

    existing = (
        db.query(PlayerInjury)
        .filter(
            PlayerInjury.player_id == body.player_id,
            PlayerInjury.report_date == unresolved.report_date,
        )
        .first()
    )
    if existing:
        injury_row = existing
    else:
        injury_row = PlayerInjury(player_id=body.player_id, report_date=unresolved.report_date)
        db.add(injury_row)

    injury_row.team_id = team_id
    injury_row.injury_type = (unresolved.injury_type or "")[:100]
    injury_row.injury_status = (unresolved.injury_status or "")[:50]
    injury_row.detail = (unresolved.detail or "")[:200]
    injury_row.season = unresolved.season
    injury_row.source = unresolved.source or "manual-resolve"
    injury_row.fetched_at = datetime.utcnow()

    db.delete(unresolved)
    db.commit()

    return {
        "status": "resolved",
        "row_id": row_id,
        "player_id": body.player_id,
        "player_name": player.full_name,
        "report_date": str(unresolved.report_date),
    }


@router.delete("/unresolved/{row_id}")
def dismiss_unresolved_injury(
    row_id: int,
    db: Session = Depends(get_db),
):
    """Dismiss an unresolved injury row (e.g. G-League call-up, not an NBA roster player)."""
    unresolved = db.query(InjurySyncUnresolved).filter(InjurySyncUnresolved.id == row_id).first()
    if not unresolved:
        raise HTTPException(status_code=404, detail="Unresolved row {0} not found.".format(row_id))
    db.delete(unresolved)
    db.commit()
    return {"status": "dismissed", "row_id": row_id}
