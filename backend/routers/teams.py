from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, SeasonStat, Team, TeamSeasonStat
from models.team import (
    TeamAvailabilityResponse,
    TeamAnalytics,
    TeamFocusLeversReport,
    TeamIntelligenceResponse,
    TeamPrepQueueResponse,
    TeamRotationReport,
    TeamRosterPlayer,
    TeamRosterResponse,
    TeamSummary,
)
from services.team_availability_service import build_team_availability
from services.team_intelligence_service import build_team_intelligence
from services.team_prep_service import build_team_prep_queue
from services.team_rotation_service import build_team_rotation_report
from services.team_focus_service import build_team_focus_levers_report

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


@router.get("/{abbr}/availability", response_model=TeamAvailabilityResponse)
def team_availability(
    abbr: str,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return the team's latest roster availability plus the next scheduled game."""
    return build_team_availability(db=db, abbr=abbr, season=season)


@router.get("/{abbr}/analytics", response_model=TeamAnalytics)
def team_analytics(
    abbr: str,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return persisted official team analytics for a season."""
    abbr_upper = abbr.upper()
    team = db.query(Team).filter(Team.abbreviation == abbr_upper).first()
    if not team:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{abbr}' not found.",
        )

    team_row = (
        db.query(TeamSeasonStat)
        .filter(
            TeamSeasonStat.team_id == team.id,
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .first()
    )

    if not team_row:
        raise HTTPException(
            status_code=404,
            detail=f"No official team analytics found for {abbr_upper} in {season}.",
        )

    return TeamAnalytics(
        team_id=team.id,
        abbreviation=abbr_upper,
        name=team.name or "",
        season=season,
        canonical_source=team_row.source,
        last_synced_at=team_row.updated_at.isoformat() if team_row.updated_at else None,
        gp=team_row.gp or 0,
        w=team_row.w or 0,
        l=team_row.l or 0,
        w_pct=round(team_row.w_pct or 0.0, 3),
        pts_pg=team_row.pts_pg,
        reb_pg=team_row.reb_pg,
        ast_pg=team_row.ast_pg,
        stl_pg=team_row.stl_pg,
        blk_pg=team_row.blk_pg,
        tov_pg=team_row.tov_pg,
        fg_pct=team_row.fg_pct,
        fg3_pct=team_row.fg3_pct,
        ft_pct=team_row.ft_pct,
        plus_minus_pg=team_row.plus_minus_pg,
        off_rating=team_row.off_rating,
        def_rating=team_row.def_rating,
        net_rating=team_row.net_rating,
        pace=team_row.pace,
        efg_pct=team_row.efg_pct,
        ts_pct=team_row.ts_pct,
        pie=team_row.pie,
        oreb_pct=team_row.oreb_pct,
        dreb_pct=team_row.dreb_pct,
        tov_pct=team_row.tov_pct,
        ast_pct=team_row.ast_pct,
        off_rating_rank=team_row.off_rating_rank,
        def_rating_rank=team_row.def_rating_rank,
        net_rating_rank=team_row.net_rating_rank,
        pace_rank=team_row.pace_rank,
        efg_pct_rank=team_row.efg_pct_rank,
        ts_pct_rank=team_row.ts_pct_rank,
        oreb_pct_rank=team_row.oreb_pct_rank,
        tov_pct_rank=team_row.tov_pct_rank,
    )


@router.get("/{abbr}/intelligence", response_model=TeamIntelligenceResponse)
def team_intelligence(
    abbr: str,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    return build_team_intelligence(db=db, abbr=abbr, season=season)


@router.get("/{abbr}/prep-queue", response_model=TeamPrepQueueResponse)
def team_prep_queue(
    abbr: str,
    season: str = Query("2024-25"),
    days: int = Query(10, ge=1, le=21),
    db: Session = Depends(get_db),
):
    return build_team_prep_queue(db=db, abbr=abbr, season=season, days=days)


@router.get("/{abbr}/rotation-report", response_model=TeamRotationReport)
def team_rotation_report(
    abbr: str,
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{abbr}' not found. View a player on that team to load it.",
        )

    return build_team_rotation_report(db=db, team=team, season=season)


@router.get("/{abbr}/focus-levers", response_model=TeamFocusLeversReport)
def team_focus_levers(
    abbr: str,
    season: str = Query("2024-25"),
    opponent: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return build_team_focus_levers_report(db=db, abbr=abbr, season=season, opponent_abbr=opponent)
