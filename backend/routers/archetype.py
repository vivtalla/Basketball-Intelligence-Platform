"""Player archetype endpoints — Sprint 67 / Stream A + Sprint 68 follow-ons."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player
from models.archetype import (
    ArchetypeHistoryEntry,
    ArchetypeHistoryResponse,
    PlayerArchetype,
)
from services.player_archetype_service import (
    METHODOLOGY_VERSION,
    build_archetype_history,
    classify_player_archetype,
)

router = APIRouter()


@router.get("/{player_id}", response_model=PlayerArchetype)
def player_archetype(
    player_id: int,
    season: str = "2024-25",
    db: Session = Depends(get_db),
) -> PlayerArchetype:
    """Classify a single player-season into one of the 15 Sprint-67 archetypes.

    Pool misses (thin sample, missing features, split-season without TOT) return
    a `developmental` response with an explanatory `reason` rather than 404.
    Spec: `specs/sprint-67-archetype-rules.md`.
    """
    return classify_player_archetype(db, player_id, season)


@router.get("/{player_id}/history", response_model=ArchetypeHistoryResponse)
def player_archetype_history(
    player_id: int,
    db: Session = Depends(get_db),
) -> ArchetypeHistoryResponse:
    """Sprint 68: multi-season archetype evolution.

    Returns every regular-season year on file for the player, oldest → newest,
    classified against each season's own peer pool. Transitions (year-over-year
    archetype changes) are flagged on each entry via `transitioned_from`.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if player is None:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found.")
    classifications = build_archetype_history(db, player_id)
    entries: list = []
    prev_key = None
    for arch in classifications:
        entries.append(ArchetypeHistoryEntry(
            season=arch.season,
            archetype_key=arch.archetype_key,
            label=arch.label,
            confidence=arch.confidence,
            reason=arch.reason,
            transitioned_from=prev_key if (prev_key is not None and prev_key != arch.archetype_key) else None,
        ))
        prev_key = arch.archetype_key
    return ArchetypeHistoryResponse(
        player_id=player_id,
        player_name=player.full_name,
        entries=entries,
        methodology_version=METHODOLOGY_VERSION,
    )
