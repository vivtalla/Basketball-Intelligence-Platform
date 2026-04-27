from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Player, PlayerAnalysisContext, PlayerInjury
from models.analysis_context import (
    AnalysisContextCreate,
    AnalysisContextResponse,
    AnalysisContextUpdate,
)


UNAVAILABLE_STATUSES = {"out", "doubtful", "questionable", "gtd", "day-to-day", "day to day"}
RECOVERY_BUFFER_DAYS = 7


def _status_key(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _is_unavailable(row: PlayerInjury) -> bool:
    status = _status_key(row.injury_status)
    return bool(status and status != "available")


def _severity(row: PlayerInjury) -> str:
    status = _status_key(row.injury_status)
    if status in {"out", "doubtful"}:
        return "high"
    if status in {"questionable", "gtd"}:
        return "medium"
    return "low"


def _applies_to_context(context: AnalysisContextResponse, facet: str) -> bool:
    applies = set(context.applies_to or ["all"])
    return "all" in applies or facet in applies


def _date_overlaps(
    start_a: Optional[date],
    end_a: Optional[date],
    start_b: Optional[date],
    end_b: Optional[date],
) -> bool:
    if start_a is None and end_a is None:
        return True
    if start_b is None and end_b is None:
        return True
    a_start = start_a or date.min
    a_end = end_a or date.max
    b_start = start_b or date.min
    b_end = end_b or date.max
    return a_start <= b_end and b_start <= a_end


def _auto_contexts_from_injuries(
    db: Session,
    player_id: int,
    season: str,
) -> List[AnalysisContextResponse]:
    rows = (
        db.query(PlayerInjury)
        .filter(
            PlayerInjury.player_id == player_id,
            PlayerInjury.season == season,
        )
        .order_by(PlayerInjury.report_date.asc())
        .all()
    )
    if not rows:
        return []

    out: List[AnalysisContextResponse] = []
    active_start: Optional[date] = None
    active_end: Optional[date] = None
    active_notes: List[str] = []
    active_severity = "low"

    for row in rows:
        if _is_unavailable(row):
            if active_start is None:
                active_start = row.report_date
                active_notes = []
                active_severity = _severity(row)
            active_end = row.return_date or row.report_date
            active_notes.append(
                " · ".join(
                    part for part in [row.injury_status, row.injury_type, row.detail] if part
                )
            )
            if _severity(row) == "high":
                active_severity = "high"
            elif _severity(row) == "medium" and active_severity == "low":
                active_severity = "medium"
            continue

        if active_start is not None:
            end_date = row.report_date
            out.append(
                AnalysisContextResponse(
                    id=None,
                    player_id=player_id,
                    season=season,
                    context_type="injury",
                    start_date=active_start,
                    end_date=end_date,
                    severity=active_severity,
                    source="injury_report_auto",
                    note="; ".join(note for note in active_notes if note) or "Injury report unavailable window.",
                    applies_to=["trend", "team_fit"],
                    created_at=None,
                    updated_at=None,
                )
            )
            if end_date:
                out.append(
                    AnalysisContextResponse(
                        id=None,
                        player_id=player_id,
                        season=season,
                        context_type="recovery",
                        start_date=end_date + timedelta(days=1),
                        end_date=end_date + timedelta(days=RECOVERY_BUFFER_DAYS),
                        severity="low",
                        source="injury_report_auto",
                        note="Short recovery buffer after injury-report return/availability.",
                        applies_to=["trend"],
                        created_at=None,
                        updated_at=None,
                    )
                )
            active_start = None
            active_end = None
            active_notes = []

    if active_start is not None:
        out.append(
            AnalysisContextResponse(
                id=None,
                player_id=player_id,
                season=season,
                context_type="injury",
                start_date=active_start,
                end_date=active_end,
                severity=active_severity,
                source="injury_report_auto",
                note="; ".join(note for note in active_notes if note) or "Latest injury-report unavailable window.",
                applies_to=["trend", "team_fit"],
                created_at=None,
                updated_at=None,
            )
        )
    return out


def _serialize_manual(row: PlayerAnalysisContext) -> AnalysisContextResponse:
    return AnalysisContextResponse(
        id=row.id,
        player_id=row.player_id,
        season=row.season,
        context_type=row.context_type,
        start_date=row.start_date,
        end_date=row.end_date,
        severity=row.severity,
        source=row.source,
        note=row.note,
        applies_to=row.applies_to or ["all"],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_analysis_contexts(
    db: Session,
    player_id: int,
    season: str,
    include_auto: bool = True,
) -> List[AnalysisContextResponse]:
    manual_rows = (
        db.query(PlayerAnalysisContext)
        .filter(
            PlayerAnalysisContext.player_id == player_id,
            PlayerAnalysisContext.season == season,
        )
        .order_by(PlayerAnalysisContext.start_date.asc().nullsfirst(), PlayerAnalysisContext.id.asc())
        .all()
    )
    contexts = [_serialize_manual(row) for row in manual_rows]
    if include_auto:
        contexts.extend(_auto_contexts_from_injuries(db, player_id, season))
    contexts.sort(key=lambda ctx: (ctx.start_date or date.min, ctx.source, ctx.id or 0))
    return contexts


def contexts_for_window(
    db: Session,
    player_id: int,
    season: str,
    start_date: Optional[date],
    end_date: Optional[date],
    facet: str,
) -> List[AnalysisContextResponse]:
    return [
        ctx for ctx in list_analysis_contexts(db, player_id, season, include_auto=True)
        if _applies_to_context(ctx, facet)
        and _date_overlaps(ctx.start_date, ctx.end_date, start_date, end_date)
    ]


def create_analysis_context(
    db: Session,
    player_id: int,
    payload: AnalysisContextCreate,
) -> AnalysisContextResponse:
    if db.query(Player).filter(Player.id == player_id).first() is None:
        raise HTTPException(status_code=404, detail="Player not found.")
    if payload.end_date and payload.start_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date.")
    row = PlayerAnalysisContext(
        player_id=player_id,
        season=payload.season,
        context_type=payload.context_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        severity=payload.severity,
        source="manual",
        note=payload.note,
        applies_to=payload.applies_to,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _serialize_manual(row)


def update_analysis_context(
    db: Session,
    player_id: int,
    context_id: int,
    payload: AnalysisContextUpdate,
) -> AnalysisContextResponse:
    row = (
        db.query(PlayerAnalysisContext)
        .filter(
            PlayerAnalysisContext.id == context_id,
            PlayerAnalysisContext.player_id == player_id,
            PlayerAnalysisContext.source == "manual",
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Manual analysis context not found.")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)
    if row.end_date and row.start_date and row.end_date < row.start_date:
        raise HTTPException(status_code=400, detail="end_date cannot be before start_date.")
    db.commit()
    db.refresh(row)
    return _serialize_manual(row)


def delete_analysis_context(db: Session, player_id: int, context_id: int) -> None:
    row = (
        db.query(PlayerAnalysisContext)
        .filter(
            PlayerAnalysisContext.id == context_id,
            PlayerAnalysisContext.player_id == player_id,
            PlayerAnalysisContext.source == "manual",
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Manual analysis context not found.")
    db.delete(row)
    db.commit()
