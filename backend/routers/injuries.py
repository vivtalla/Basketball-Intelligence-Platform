"""Injuries router: current injury report and per-player injury history."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import InjurySyncUnresolved, Player, PlayerInjury, Team
from models.injury import (
    PlayerDurationEstimateResponse,
    TeamAvailabilityImpact,
)
from services.availability_impact_service import (
    _normalize_body_part as _normalize_body_part_text,
    compute_team_availability_impact_by_abbr,
)
from services.injury_duration_model import (
    expected_duration,
    find_similar_past_injuries,
    player_age,
    player_recurrence_for_body_part,
)
from services.sync_service import sync_injuries

router = APIRouter()


# `_normalize_body_part_text` is reused so the duration-estimate endpoint
# and the team panel agree on body-part labels (knee, hamstring, etc.).


_DURATION_METHODOLOGY_NOTE = (
    "Empirical median / interquartile range computed from the player_injury_history "
    "table, filtered to the same body part and a +/-3y age band. Falls back to a "
    "hardcoded prior when fewer than 5 comparable historical injuries are available."
)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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


@router.get(
    "/{player_id}/duration-estimate",
    response_model=PlayerDurationEstimateResponse,
)
def get_player_duration_estimate(
    player_id: int,
    body_part: Optional[str] = Query(
        None,
        description=(
            "Override body-part keyword. Defaults to the latest injury report's "
            "injury_type/detail mapped to the model vocabulary."
        ),
    ),
    db: Session = Depends(get_db),
):
    """Empirical injury-duration estimate + similar past injuries for a player.

    Sprint 78 FO5. Backs the player-profile injury panel.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player {0} not found.".format(player_id))

    latest_injury = (
        db.query(PlayerInjury)
        .filter(PlayerInjury.player_id == player_id)
        .order_by(PlayerInjury.report_date.desc())
        .first()
    )

    resolved_body_part = (body_part or "").strip().lower() or None
    if not resolved_body_part and latest_injury is not None:
        resolved_body_part = _normalize_body_part_text(
            latest_injury.injury_type, latest_injury.detail
        )

    if not resolved_body_part:
        # Fall back to the most-frequent historical body part for this player so
        # the panel always renders something reasonable.
        from db.models import PlayerInjuryHistory

        common = (
            db.query(PlayerInjuryHistory.body_part)
            .filter(PlayerInjuryHistory.player_id == player_id)
            .all()
        )
        if common:
            counts = {}
            for row in common:
                counts[row[0]] = counts.get(row[0], 0) + 1
            resolved_body_part = max(counts, key=counts.get)

    if not resolved_body_part:
        # Last resort: report a generic prior so downstream UI doesn't crash.
        resolved_body_part = "ankle"

    age = player_age(player)
    is_recurring = player_recurrence_for_body_part(db, player_id, resolved_body_part)
    estimate = expected_duration(
        db,
        body_part=resolved_body_part,
        age=age,
        is_recurring=is_recurring,
    )
    similar = find_similar_past_injuries(
        db,
        body_part=resolved_body_part,
        age=age,
        limit=3,
        exclude_player_id=player_id,
    )

    return PlayerDurationEstimateResponse(
        player_id=player.id,
        player_name=player.full_name,
        body_part=resolved_body_part,
        severity=(latest_injury.injury_status if latest_injury else None),
        age=age,
        is_recurring=is_recurring,
        current_injury_status=latest_injury.injury_status if latest_injury else None,
        current_injury_detail=latest_injury.detail if latest_injury else None,
        current_injury_report_date=latest_injury.report_date if latest_injury else None,
        current_injury_return_date=latest_injury.return_date if latest_injury else None,
        estimate=estimate,
        similar_past_injuries=similar,
        methodology_note=_DURATION_METHODOLOGY_NOTE,
    )


@router.get(
    "/team/{team_abbr}/availability-impact",
    response_model=TeamAvailabilityImpact,
)
def get_team_availability_impact(
    team_abbr: str,
    season: str = Query("2024-25", description="Season string e.g. 2024-25"),
    db: Session = Depends(get_db),
):
    """Project the net-rating + rotation impact of currently-sidelined players.

    Sprint 78 FO5. Backs the team page Availability Impact panel.
    """
    return compute_team_availability_impact_by_abbr(db, team_abbr=team_abbr, season=season)


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
