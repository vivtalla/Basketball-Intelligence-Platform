from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from data.nba_client import search_players
from db.database import get_db
from models.player import PlayerProfile, PlayerSearchResult, PlayerTrendReport
from services.player_trend_service import build_player_trend_report
from services.sync_service import canonical_player_name, get_or_sync_player_profile, sync_player_if_needed

router = APIRouter()


@router.get("/search", response_model=List[PlayerSearchResult])
def search(q: str = Query(..., min_length=2, description="Player name to search")):
    results = search_players(q)
    return results


@router.get("/{player_id}", response_model=PlayerProfile)
def get_player(player_id: int, db: Session = Depends(get_db)):
    try:
        player = get_or_sync_player_profile(db, player_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Player not found: {e}")

    team_abbr = ""
    team_name = ""
    if player.team:
        team_abbr = player.team.abbreviation
        team_name = player.team.name

    return PlayerProfile(
        id=player.id,
        full_name=canonical_player_name(player.full_name, player.first_name or "", player.last_name or ""),
        first_name=player.first_name or "",
        last_name=player.last_name or "",
        team_name=team_name,
        team_abbreviation=team_abbr,
        team_id=player.team_id,
        jersey=player.jersey or "",
        position=player.position or "",
        height=player.height or "",
        weight=player.weight or "",
        birth_date=player.birth_date or "",
        country=player.country or "",
        school=player.school,
        draft_year=player.draft_year,
        draft_round=player.draft_round,
        draft_number=player.draft_number,
        from_year=player.from_year,
        to_year=player.to_year,
        headshot_url=player.headshot_url or "",
    )


@router.post("/{player_id}/sync")
def resync_player(player_id: int, db: Session = Depends(get_db)):
    """Force re-sync a player's data from NBA.com."""
    from services.sync_service import sync_player
    try:
        sync_player(db, player_id)
        return {"status": "ok", "message": f"Player {player_id} synced"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {e}")


@router.get("/{player_id}/trend-report", response_model=PlayerTrendReport)
def get_player_trend_report(
    player_id: int,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    try:
        player = sync_player_if_needed(db, player_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Player not found: {e}")

    return build_player_trend_report(db=db, player=player, season=season)
