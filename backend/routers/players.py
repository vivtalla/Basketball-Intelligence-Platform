from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from db.models import Player
from models.mvp import MvpGravityProfile
from models.player import PlayerProfile, PlayerSearchResult, PlayerTrendReport
from services.gravity_service import build_gravity_profile
from services.player_trend_service import build_player_trend_report
from services.sync_service import canonical_player_name

router = APIRouter()

_PROFILE_STALE_AFTER = timedelta(days=14)


def _profile_data_status(player: Player) -> str:
    if not player:
        return "missing"
    updated_at = getattr(player, "updated_at", None)
    if player.is_active and updated_at and (datetime.utcnow() - updated_at) > _PROFILE_STALE_AFTER:
        return "stale"
    return "ready"


def _empty_profile(player_id: int) -> PlayerProfile:
    return PlayerProfile(
        id=player_id,
        full_name="",
        first_name="",
        last_name="",
        team_name="",
        team_abbreviation="",
        team_id=None,
        jersey="",
        position="",
        height="",
        weight="",
        birth_date="",
        country="",
        school=None,
        draft_year=None,
        draft_round=None,
        draft_number=None,
        from_year=None,
        to_year=None,
        headshot_url="",
        data_status="missing",
        last_synced_at=None,
    )


@router.get("/search", response_model=List[PlayerSearchResult])
def search(
    q: str = Query(..., min_length=2, description="Player name to search"),
    db: Session = Depends(get_db),
):
    query = f"%{q.strip()}%"
    rows = (
        db.query(Player)
        .filter(
            or_(
                Player.full_name.ilike(query),
                Player.first_name.ilike(query),
                Player.last_name.ilike(query),
            )
        )
        .order_by(Player.is_active.desc(), Player.full_name.asc())
        .limit(20)
        .all()
    )
    return [
        PlayerSearchResult(
            id=row.id,
            full_name=canonical_player_name(row.full_name, row.first_name or "", row.last_name or ""),
            is_active=bool(row.is_active),
        )
        for row in rows
    ]


@router.get("/{player_id}", response_model=PlayerProfile)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        return _empty_profile(player_id)

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
        data_status=_profile_data_status(player),
        last_synced_at=player.updated_at.isoformat() if player.updated_at else None,
    )


@router.get("/{player_id}/gravity", response_model=MvpGravityProfile)
def get_player_gravity(
    player_id: int,
    season: str = Query(default=None, description="Season string, e.g. 2025-26"),
    season_type: str = Query(default="Regular Season"),
    db: Session = Depends(get_db),
) -> MvpGravityProfile:
    """Return one player's DB-first Gravity profile for player pages and stat workspaces."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found in local warehouse.")
    resolved_season = season or _active_nba_season()
    return build_gravity_profile(db, player_id=player_id, season=resolved_season, season_type=season_type)


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
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found in local warehouse.")

    return build_player_trend_report(db=db, player=player, season=season)
