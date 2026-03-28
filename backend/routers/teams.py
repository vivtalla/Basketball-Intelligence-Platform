from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from data.nba_client import get_team_stats
from db.database import get_db
from db.models import Player, SeasonStat, Team
from models.team import TeamAnalytics, TeamRosterPlayer, TeamRosterResponse, TeamSummary

router = APIRouter()


@router.get("", response_model=List[TeamSummary])
def list_teams(db: Session = Depends(get_db)):
    """List all teams in the database with their synced player counts."""
    teams = db.query(Team).order_by(Team.name).all()
    result = []
    for team in teams:
        count = (
            db.query(Player)
            .filter(Player.team_id == team.id, Player.is_active == True)  # noqa: E712
            .count()
        )
        result.append(
            TeamSummary(
                team_id=team.id,
                abbreviation=team.abbreviation,
                name=team.name,
                player_count=count,
            )
        )
    return result


@router.get("/{abbr}", response_model=TeamRosterResponse)
def team_roster(abbr: str, db: Session = Depends(get_db)):
    """Return team info and the roster of synced players with their latest season stats."""
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{abbr}' not found in database. View a player on that team first to load it.")

    players = (
        db.query(Player)
        .filter(Player.team_id == team.id, Player.is_active == True)  # noqa: E712
        .order_by(Player.last_name)
        .all()
    )

    roster = []
    synced_count = 0
    for player in players:
        stat = (
            db.query(SeasonStat)
            .filter(SeasonStat.player_id == player.id, SeasonStat.is_playoff == False)  # noqa: E712
            .order_by(SeasonStat.season.desc())
            .first()
        )
        roster.append(
            TeamRosterPlayer(
                player_id=player.id,
                full_name=player.full_name,
                position=player.position or "",
                jersey=player.jersey or "",
                headshot_url=player.headshot_url or "",
                season=stat.season if stat else None,
                pts_pg=stat.pts_pg if stat else None,
                reb_pg=stat.reb_pg if stat else None,
                ast_pg=stat.ast_pg if stat else None,
                per=stat.per if stat else None,
                bpm=stat.bpm if stat else None,
            )
        )
        if stat:
            synced_count += 1

    return TeamRosterResponse(
        team_id=team.id,
        abbreviation=team.abbreviation,
        name=team.name,
        players=roster,
        synced_count=synced_count,
    )


@router.get("/{abbr}/analytics", response_model=TeamAnalytics)
def team_analytics(
    abbr: str,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return team-level advanced analytics for a season from NBA.com stats API."""
    abbr_upper = abbr.upper()
    team = db.query(Team).filter(Team.abbreviation == abbr_upper).first()
    if not team:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{abbr}' not found. View a player on that team to load it.",
        )

    try:
        all_team_stats = get_team_stats(season)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"NBA API error: {exc}") from exc

    stats = all_team_stats.get(abbr_upper)
    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"No stats found for {abbr_upper} in {season}.",
        )

    return TeamAnalytics(**stats)
