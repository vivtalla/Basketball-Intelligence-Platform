"""Advanced stats endpoints: on/off splits, clutch stats, lineup analysis."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.nba_client import get_player_game_ids
from db.database import get_db
from db.models import PlayerOnOff, SeasonStat, LineupStats, Player, GameLog, PlayByPlay
from models.stats import PbpCoverage
from services.pbp_sync_service import sync_pbp_for_player, sync_pbp_for_season
from services.sync_service import sync_player_if_needed

router = APIRouter()


@router.post("/sync-season")
def sync_season_pbp(season: str, force_refresh: bool = False):
    """Fetch or reuse season play-by-play and rebuild derived season metrics."""
    try:
        return sync_pbp_for_season(season, force_refresh=force_refresh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PBP season sync failed: {exc}")


@router.post("/{player_id}/sync-pbp")
def sync_player_pbp(player_id: int, season: str, db: Session = Depends(get_db), force_refresh: bool = False):
    """Fetch or reuse player-season play-by-play and rebuild player-level derived stats."""
    try:
        sync_player_if_needed(db, player_id)
        return sync_pbp_for_player(player_id, season, force_refresh=force_refresh)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PBP player sync failed: {exc}")


@router.get("/{player_id}/on-off")
def get_on_off(player_id: int, season: str = "2024-25", db: Session = Depends(get_db)):
    """Return on/off split ratings for a player in a given season."""
    row = db.query(PlayerOnOff).filter_by(player_id=player_id, season=season, is_playoff=False).first()
    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"No on/off data for player {player_id} in {season}. Run pbp_import.py first."
        )
    return {
        "player_id": player_id,
        "season": season,
        "on_minutes": row.on_minutes,
        "off_minutes": row.off_minutes,
        "on_net_rating": row.on_net_rating,
        "off_net_rating": row.off_net_rating,
        "on_off_net": row.on_off_net,
        "on_ortg": row.on_ortg,
        "on_drtg": row.on_drtg,
        "off_ortg": row.off_ortg,
        "off_drtg": row.off_drtg,
    }


@router.get("/{player_id}/clutch")
def get_clutch(player_id: int, season: str = "2024-25", db: Session = Depends(get_db)):
    """Return clutch stats for a player (last 5 min, within 5 pts)."""
    row = db.query(SeasonStat).filter_by(player_id=player_id, season=season, is_playoff=False).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No season stats for player {player_id} in {season}.")
    if row.clutch_pts is None:
        raise HTTPException(
            status_code=404,
            detail=f"No clutch data for player {player_id} in {season}. Run pbp_import.py first."
        )
    return {
        "player_id": player_id,
        "season": season,
        "clutch_pts": row.clutch_pts,
        "clutch_fga": row.clutch_fga,
        "clutch_fg_pct": row.clutch_fg_pct,
        "clutch_plus_minus": row.clutch_plus_minus,
        "second_chance_pts": row.second_chance_pts,
        "fast_break_pts": row.fast_break_pts,
    }


@router.get("/{player_id}/pbp-coverage", response_model=PbpCoverage)
def get_pbp_coverage(player_id: int, season: str = "2024-25", db: Session = Depends(get_db)):
    """Return play-by-play sync coverage metadata for a player-season."""
    sync_player_if_needed(db, player_id)

    season_row = (
        db.query(SeasonStat)
        .filter_by(player_id=player_id, season=season, is_playoff=False)
        .first()
    )
    if not season_row:
        raise HTTPException(status_code=404, detail=f"No season stats for player {player_id} in {season}.")

    try:
        player_game_ids = get_player_game_ids(player_id, season)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not determine player games for coverage: {exc}")

    eligible_games = len(player_game_ids)
    synced_games = 0
    if player_game_ids:
        synced_games = (
            db.query(func.count(func.distinct(PlayByPlay.game_id)))
            .join(GameLog, PlayByPlay.game_id == GameLog.game_id)
            .filter(
                GameLog.season == season,
                PlayByPlay.game_id.in_(player_game_ids),
            )
            .scalar()
            or 0
        )

    on_off_row = db.query(PlayerOnOff).filter_by(
        player_id=player_id,
        season=season,
        is_playoff=False,
    ).first()

    has_on_off = bool(on_off_row and on_off_row.on_off_net is not None)
    has_scoring_splits = any(
        value is not None
        for value in [
            season_row.clutch_pts,
            season_row.clutch_fg_pct,
            season_row.second_chance_pts,
            season_row.fast_break_pts,
        ]
    )

    timestamps: list[datetime] = []
    if on_off_row and on_off_row.updated_at:
        timestamps.append(on_off_row.updated_at)
    if season_row.updated_at and (has_on_off or has_scoring_splits):
        timestamps.append(season_row.updated_at)

    if synced_games == 0 and not has_on_off and not has_scoring_splits:
        status = "none"
    elif eligible_games > 0 and synced_games >= eligible_games and has_on_off and has_scoring_splits:
        status = "ready"
    else:
        status = "partial"

    return PbpCoverage(
        player_id=player_id,
        season=season,
        eligible_games=eligible_games,
        synced_games=synced_games,
        has_on_off=has_on_off,
        has_scoring_splits=has_scoring_splits,
        status=status,
        last_derived_at=max(timestamps).isoformat() if timestamps else None,
    )


@router.get("/lineups")
def get_lineups(
    season: str = "2024-25",
    team_id: Optional[int] = None,
    min_minutes: float = 5.0,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    """Return top 5-man lineups by net rating for a season."""
    query = db.query(LineupStats).filter(
        LineupStats.season == season,
        LineupStats.minutes >= min_minutes,
        LineupStats.net_rating.isnot(None),
    )
    if team_id:
        query = query.filter(LineupStats.team_id == team_id)

    rows = query.order_by(LineupStats.net_rating.desc()).limit(limit).all()

    results = []
    for row in rows:
        player_ids = [int(pid) for pid in row.lineup_key.split("-")]
        # Resolve player names
        players = db.query(Player).filter(Player.id.in_(player_ids)).all()
        name_map = {p.id: p.full_name for p in players}
        player_names = [name_map.get(pid, str(pid)) for pid in player_ids]

        results.append({
            "lineup_key": row.lineup_key,
            "player_ids": player_ids,
            "player_names": player_names,
            "season": row.season,
            "team_id": row.team_id,
            "minutes": row.minutes,
            "net_rating": row.net_rating,
            "ortg": row.ortg,
            "drtg": row.drtg,
            "plus_minus": row.plus_minus,
            "possessions": row.possessions,
        })

    return {"season": season, "lineups": results}


@router.get("/on-off-leaderboard")
def get_on_off_leaderboard(
    season: str = "2024-25",
    min_minutes: float = 200.0,
    limit: int = 25,
    db: Session = Depends(get_db),
):
    """Return players ranked by on/off net rating differential."""
    rows = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,
            PlayerOnOff.on_minutes >= min_minutes,
            PlayerOnOff.on_off_net.isnot(None),
        )
        .order_by(PlayerOnOff.on_off_net.desc())
        .limit(limit)
        .all()
    )

    results = []
    for row in rows:
        player = db.query(Player).filter_by(id=row.player_id).first()
        results.append({
            "player_id": row.player_id,
            "player_name": player.full_name if player else str(row.player_id),
            "on_minutes": row.on_minutes,
            "on_net_rating": row.on_net_rating,
            "off_net_rating": row.off_net_rating,
            "on_off_net": row.on_off_net,
        })

    return {"season": season, "players": results}
