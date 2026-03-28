"""Player similarity endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import SeasonStat
from services.similarity_service import find_similar_players

router = APIRouter()


@router.get("/{player_id}")
def similar_players(
    player_id: int,
    season: str = "2024-25",
    n: int = 8,
    cross_era: bool = True,
    db: Session = Depends(get_db),
):
    """Return the top-N most statistically similar player-seasons.

    Similarity is computed via weighted Euclidean distance on z-score-normalized
    stats (normalized within each season to remove era bias).

    cross_era=true compares across all available seasons.
    cross_era=false restricts to the same season only.
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
        "comps": results,
    }
