from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import PreReadSnapshot
from models.pre_read import (
    PreReadContext,
    PreReadDeckResponse,
    PreReadSnapshotCreateRequest,
    PreReadSnapshotListResponse,
    PreReadSnapshotRef,
    PreReadSnapshotResponse,
    PreReadSnapshotSummary,
)
from services.pre_read_service import build_pre_read_deck


def _share_url(snapshot_id: str) -> str:
    return "/pre-read?snapshot_id={0}".format(snapshot_id)


def _deck_from_payload(payload: dict) -> PreReadDeckResponse:
    return PreReadDeckResponse(**payload)


def create_pre_read_snapshot(db: Session, payload: PreReadSnapshotCreateRequest) -> PreReadSnapshotResponse:
    snapshot_id = str(uuid.uuid4())
    snapshot_ref = PreReadSnapshotRef(
        snapshot_id=snapshot_id,
        share_url=_share_url(snapshot_id),
        created_at="",
    )
    context = PreReadContext(
        team_abbreviation=payload.team.upper(),
        opponent_abbreviation=payload.opponent.upper(),
        season=payload.season,
        game_id=payload.game_id,
        source_view=payload.source_view,
        source_snapshot_id=payload.source_snapshot_id,
        extras=payload.context,
    )
    deck = build_pre_read_deck(
        db=db,
        team=payload.team,
        opponent=payload.opponent,
        season=payload.season,
        snapshot_ref=snapshot_ref,
        source_context=context,
    )
    snapshot_ref.created_at = deck.generated_at or ""
    deck.snapshot = snapshot_ref

    row = PreReadSnapshot(
        snapshot_id=snapshot_id,
        team_abbreviation=payload.team.upper(),
        opponent_abbreviation=payload.opponent.upper(),
        season=payload.season,
        game_id=payload.game_id,
        saved_from=payload.source_view,
        payload=json.loads(deck.model_dump_json()),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    created_at = row.created_at.isoformat() if row.created_at else deck.generated_at or ""
    deck.snapshot = PreReadSnapshotRef(
        snapshot_id=snapshot_id,
        share_url=_share_url(snapshot_id),
        created_at=created_at,
    )
    return PreReadSnapshotResponse(
        snapshot_id=snapshot_id,
        share_url=_share_url(snapshot_id),
        created_at=created_at,
        context=context,
        deck=deck,
    )


def get_pre_read_snapshot(db: Session, snapshot_id: str) -> PreReadSnapshotResponse:
    row = (
        db.query(PreReadSnapshot)
        .filter(PreReadSnapshot.snapshot_id == snapshot_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Pre-read snapshot not found.")

    created_at = row.created_at.isoformat() if row.created_at else ""
    deck = _deck_from_payload(row.payload)
    deck.snapshot = PreReadSnapshotRef(
        snapshot_id=row.snapshot_id,
        share_url=_share_url(row.snapshot_id),
        created_at=created_at,
    )
    return PreReadSnapshotResponse(
        snapshot_id=row.snapshot_id,
        share_url=_share_url(row.snapshot_id),
        created_at=created_at,
        context=PreReadContext(
            team_abbreviation=row.team_abbreviation,
            opponent_abbreviation=row.opponent_abbreviation,
            season=row.season,
            game_id=row.game_id,
            source_view=row.saved_from,
        ),
        deck=deck,
    )


def list_pre_read_snapshots(
    db: Session,
    team: Optional[str] = None,
    opponent: Optional[str] = None,
    season: Optional[str] = None,
    limit: int = 10,
) -> PreReadSnapshotListResponse:
    query = db.query(PreReadSnapshot)
    if team:
        query = query.filter(PreReadSnapshot.team_abbreviation == team.upper())
    if opponent:
        query = query.filter(PreReadSnapshot.opponent_abbreviation == opponent.upper())
    if season:
        query = query.filter(PreReadSnapshot.season == season)

    rows = (
        query.order_by(PreReadSnapshot.created_at.desc(), PreReadSnapshot.id.desc())
        .limit(limit)
        .all()
    )
    items = []
    for row in rows:
        deck = _deck_from_payload(row.payload)
        items.append(
            PreReadSnapshotSummary(
                snapshot_id=row.snapshot_id,
                share_url=_share_url(row.snapshot_id),
                created_at=row.created_at.isoformat() if row.created_at else "",
                team_abbreviation=row.team_abbreviation,
                opponent_abbreviation=row.opponent_abbreviation,
                season=row.season,
                game_id=row.game_id,
                prep_headline=deck.prep_context.headline if deck.prep_context else None,
                saved_from=row.saved_from,
            )
        )
    return PreReadSnapshotListResponse(items=items)
