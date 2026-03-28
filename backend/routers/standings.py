from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from data.nba_client import get_standings_data
from db.database import get_db
from db.models import Team
from models.standings import StandingsEntry

router = APIRouter()


@router.get("", response_model=List[StandingsEntry])
def get_standings(
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return league standings for a season, enriched with team abbreviations."""
    # Build team_id → abbreviation lookup from DB
    team_abbr: dict[int, str] = {
        t.id: t.abbreviation for t in db.query(Team).all()
    }

    try:
        rows = get_standings_data(season)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NBA API error: {exc}") from exc

    result = []
    for row in rows:
        row["abbreviation"] = team_abbr.get(row["team_id"], "")
        result.append(StandingsEntry(**row))

    # Sort each conference by playoff_rank
    result.sort(key=lambda e: (e.conference, e.playoff_rank))
    return result
