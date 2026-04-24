"""Player archetype endpoint — Sprint 67 / Stream A."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from models.archetype import PlayerArchetype
from services.player_archetype_service import classify_player_archetype

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
