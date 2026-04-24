"""Player similarity endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import SeasonStat
from services.similarity_service import (
    find_similar_players,
    find_similar_players_with_archetype,
)

router = APIRouter()


@router.get("/{player_id}")
def similar_players(
    player_id: int,
    season: str = "2024-25",
    n: int = 8,
    cross_era: bool = True,
    mode: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Return the top-N most statistically similar player-seasons.

    Two paths:

    - Legacy (default, `mode` omitted): weighted Euclidean distance on 9 z-score-
      normalized box stats. `cross_era=true` compares across all seasons;
      `cross_era=false` restricts to the same season.
    - Sprint 67/68 role-aware (`mode` set): extended 13-feature distance with
      archetype labels attached to every comp. Supported values:
      `season` (same-season league-wide), `age` (age ±1 across all seasons),
      `team_fit` (same-season league-wide with a teammate-duplicate penalty —
      features where the subject's z-score is within 0.5 of a same-team
      teammate's z-score carry a 0.4× distance weight, so comps that
      complement gaps rank ahead of comps that duplicate existing strengths).
    """
    # Verify the target player-season has enough data
    target = db.query(SeasonStat).filter_by(
        player_id=player_id, season=season, is_playoff=False
    ).first()
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"No stats for player {player_id} in {season}. Sync the player first.",
        )

    if mode is None:
        results = find_similar_players(db, player_id, season, n=n, cross_era=cross_era)
        if not results:
            raise HTTPException(
                status_code=404,
                detail="Not enough data to compute similarity. Player may lack required stats.",
            )
        return {
            "player_id": player_id,
            "season": season,
            "cross_era": cross_era,
            "mode": "legacy",
            "comps": results,
        }

    if mode not in ("season", "age", "team_fit"):
        raise HTTPException(status_code=400, detail=f"unknown mode '{mode}'")

    results = find_similar_players_with_archetype(
        db, player_id, season, mode=mode, n=n,
    )
    if not results:
        raise HTTPException(
            status_code=404,
            detail="Not enough data to compute similarity. Player may lack required stats.",
        )
    return {
        "player_id": player_id,
        "season": season,
        "mode": mode,
        "comps": results,
    }
