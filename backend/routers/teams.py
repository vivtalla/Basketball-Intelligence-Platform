from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, PlayerGameLog, SeasonStat, Team
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
    """Return team-level analytics computed from synced player season stats."""
    abbr_upper = abbr.upper()
    team = db.query(Team).filter(Team.abbreviation == abbr_upper).first()
    if not team:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{abbr}' not found.",
        )

    player_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.team_abbreviation == abbr_upper,
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= 1,
        )
        .all()
    )

    if not player_rows:
        raise HTTPException(
            status_code=404,
            detail=f"No stats found for {abbr_upper} in {season}.",
        )

    # Team GP = the most games played by any player on this team
    team_gp = max((r.gp or 0) for r in player_rows)
    if team_gp == 0:
        raise HTTPException(status_code=404, detail="No games found.")

    # Sum raw counting stats from season totals
    total_pts  = sum(r.pts  or 0 for r in player_rows)
    total_reb  = sum(r.reb  or 0 for r in player_rows)
    total_ast  = sum(r.ast  or 0 for r in player_rows)
    total_stl  = sum(r.stl  or 0 for r in player_rows)
    total_blk  = sum(r.blk  or 0 for r in player_rows)
    total_tov  = sum(r.tov  or 0 for r in player_rows)
    total_fgm  = sum(r.fgm  or 0 for r in player_rows)
    total_fga  = sum(r.fga  or 0 for r in player_rows)
    total_fg3m = sum(r.fg3m or 0 for r in player_rows)
    total_fg3a = sum(r.fg3a or 0 for r in player_rows)
    total_ftm  = sum(r.ftm  or 0 for r in player_rows)
    total_fta  = sum(r.fta  or 0 for r in player_rows)

    def _safe_div(n: float, d: float) -> Optional[float]:
        return round(n / d, 3) if d else None

    fg_pct  = _safe_div(total_fgm,  total_fga)
    fg3_pct = _safe_div(total_fg3m, total_fg3a)
    ft_pct  = _safe_div(total_ftm,  total_fta)

    # GP-weighted average for per-game and efficiency fields
    def _wavg(attr: str) -> Optional[float]:
        pairs = [(getattr(r, attr), r.gp or 0) for r in player_rows if getattr(r, attr) is not None]
        total_w = sum(w for _, w in pairs)
        if not pairs or total_w == 0:
            return None
        return sum(v * w for v, w in pairs) / total_w

    # W/L from player game logs (distinct games for this team)
    wl_rows = (
        db.query(PlayerGameLog.game_id, PlayerGameLog.wl)
        .filter(
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
            PlayerGameLog.matchup.like(f"{abbr_upper} %"),
            PlayerGameLog.wl.in_(["W", "L"]),
        )
        .distinct()
        .all()
    )
    wins   = sum(1 for r in wl_rows if r.wl == "W")
    losses = sum(1 for r in wl_rows if r.wl == "L")
    gp_wl  = wins + losses
    w_pct  = wins / gp_wl if gp_wl else 0.0

    return TeamAnalytics(
        team_id=team.id,
        abbreviation=abbr_upper,
        name=team.name or "",
        season=season,
        gp=team_gp,
        w=wins,
        l=losses,
        w_pct=round(w_pct, 3),
        pts_pg=round(total_pts / team_gp, 1) if team_gp else None,
        reb_pg=round(total_reb / team_gp, 1) if team_gp else None,
        ast_pg=round(total_ast / team_gp, 1) if team_gp else None,
        stl_pg=round(total_stl / team_gp, 1) if team_gp else None,
        blk_pg=round(total_blk / team_gp, 1) if team_gp else None,
        tov_pg=round(total_tov / team_gp, 1) if team_gp else None,
        fg_pct=fg_pct,
        fg3_pct=fg3_pct,
        ft_pct=ft_pct,
        plus_minus_pg=None,
        off_rating=_wavg("off_rating"),
        def_rating=_wavg("def_rating"),
        net_rating=_wavg("net_rating"),
        pace=_wavg("pace"),
        efg_pct=_wavg("efg_pct"),
        ts_pct=_wavg("ts_pct"),
        pie=_wavg("pie"),
        oreb_pct=_wavg("oreb_pct"),
        dreb_pct=None,
        tov_pct=None,
        ast_pct=None,
        off_rating_rank=None,
        def_rating_rank=None,
        net_rating_rank=None,
        pace_rank=None,
        efg_pct_rank=None,
        ts_pct_rank=None,
        oreb_pct_rank=None,
        tov_pct_rank=None,
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
    db: Session = Depends(get_db),
):
    return build_team_focus_levers_report(db=db, abbr=abbr, season=season)
