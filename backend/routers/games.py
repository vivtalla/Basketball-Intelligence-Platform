from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from models.game import (
    GameDetailResponse,
    GameSummaryResponse,
    GameVisualizationResponse,
)
from services.game_detail_assembler import assemble_game_detail
from services.game_summary_service import get_game_summary
from services.game_visualization_service import build_game_visualization

router = APIRouter()


@router.get("/{game_id}/summary", response_model=GameSummaryResponse)
def get_game_summary_route(game_id: str, db: Session = Depends(get_db)):
    summary = get_game_summary(db, game_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found.")
    return summary


@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game_detail(game_id: str, db: Session = Depends(get_db)):
    # Sprint 77 — single-stop assembler composes the legacy box-score walk
    # with WP/lead (EA1), possession diary + per-quarter +/- (EA2), and
    # post-game series odds history (EA3). Each derived component is
    # independently fault-tolerant; the 404s for missing game / missing PBP
    # still propagate from the base builder.
    return assemble_game_detail(db, game_id)


@router.get("/{game_id}/visualization", response_model=GameVisualizationResponse)
def get_game_visualization(
    game_id: str,
    shot_event_id: Optional[str] = Query(None),
    player_id: Optional[int] = Query(None),
    period: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    source_surface: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    source_label: Optional[str] = Query(None),
    reason: Optional[str] = Query(None),
    claim_id: Optional[str] = Query(None),
    clip_anchor_id: Optional[str] = Query(None),
    return_to: Optional[str] = Query(None),
    linkage_quality: Optional[str] = Query(None),
    focus_event_id: Optional[str] = Query(None),
    focus_action_number: Optional[int] = Query(None),
    focus_window: int = Query(1, ge=1, le=4),
    db: Session = Depends(get_db),
):
    payload = build_game_visualization(
        db,
        game_id=game_id,
        shot_event_id=shot_event_id,
        player_id=player_id,
        period=period,
        event_type=event_type,
        query=query,
        source=source,
        source_surface=source_surface,
        source_id=source_id,
        source_label=source_label,
        reason=reason,
        claim_id=claim_id,
        clip_anchor_id=clip_anchor_id,
        return_to=return_to,
        linkage_quality=linkage_quality,
        focus_event_id=focus_event_id,
        focus_action_number=focus_action_number,
        focus_window=focus_window,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"No visualization payload found for game {game_id}.")
    return payload
