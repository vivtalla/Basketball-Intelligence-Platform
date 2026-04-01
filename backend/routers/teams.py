from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import GameLog, LineupStats, PlayByPlay, Player, PlayerGameLog, PlayerOnOff, SeasonStat, Team
from models.team import (
    TeamAnalytics,
    TeamFocusLeversReport,
    TeamImpactLeader,
    TeamIntelligenceResponse,
    TeamPbpCoverage,
    TeamRecentGame,
    TeamRotationReport,
    TeamRosterPlayer,
    TeamRosterResponse,
    TeamSummary,
)
from services.team_rotation_service import build_team_rotation_report
from services.team_focus_service import build_team_focus_levers_report

router = APIRouter()


def _serialize_lineup(row: LineupStats, db: Session):
    player_ids = [int(pid) for pid in row.lineup_key.split("-")]
    players = db.query(Player).filter(Player.id.in_(player_ids)).all()
    name_map = {p.id: p.full_name for p in players}
    player_names = [name_map.get(pid, str(pid)) for pid in player_ids]
    return {
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
    }


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
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(
            status_code=404,
            detail=f"Team '{abbr}' not found. View a player on that team to load it.",
        )

    roster_players = (
        db.query(Player)
        .filter(Player.team_id == team.id, Player.is_active == True)  # noqa: E712
        .all()
    )
    player_ids = [player.id for player in roster_players]

    team_games = (
        db.query(GameLog)
        .filter(
            GameLog.season == season,
            (GameLog.home_team_id == team.id) | (GameLog.away_team_id == team.id),
        )
        .order_by(GameLog.game_date.desc().nullslast(), GameLog.game_id.desc())
        .all()
    )
    eligible_games = len(team_games)
    team_game_ids = [game.game_id for game in team_games]
    completed_games = [
        game for game in team_games if game.home_score is not None and game.away_score is not None
    ]

    synced_games = 0
    if team_game_ids:
        synced_games = (
            db.query(func.count(func.distinct(PlayByPlay.game_id)))
            .filter(PlayByPlay.game_id.in_(team_game_ids))
            .scalar()
            or 0
        )

    season_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id.in_(player_ids) if player_ids else False,
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    ) if player_ids else []
    season_map = {row.player_id: row for row in season_rows}

    on_off_rows = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.player_id.in_(player_ids) if player_ids else False,
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
            PlayerOnOff.on_off_net.isnot(None),
        )
        .order_by(PlayerOnOff.on_off_net.desc())
        .all()
    ) if player_ids else []

    players_with_on_off = len(on_off_rows)
    players_with_scoring_splits = sum(
        1
        for row in season_rows
        if any(
            value is not None
            for value in [
                row.clutch_pts,
                row.clutch_fg_pct,
                row.second_chance_pts,
                row.fast_break_pts,
            ]
        )
    )

    if synced_games == 0 and players_with_on_off == 0 and players_with_scoring_splits == 0:
        coverage_status = "none"
    elif eligible_games > 0 and synced_games >= eligible_games and players_with_on_off >= max(1, len(player_ids) // 3):
        coverage_status = "ready"
    else:
        coverage_status = "partial"

    recent_games = []
    recent_wins = 0
    recent_count = 0
    recent_margin_total = 0.0
    total_wins = 0
    total_losses = 0
    total_team_points = 0
    total_opp_points = 0
    streak_result = None
    streak_length = 0
    team_lookup = {
        t.id: t.abbreviation for t in db.query(Team).filter(Team.id.in_(
            [game.home_team_id for game in team_games] + [game.away_team_id for game in team_games]
        )).all()
    } if team_games else {}

    for game in team_games[:10]:
        is_home = game.home_team_id == team.id
        team_score = game.home_score if is_home else game.away_score
        opponent_score = game.away_score if is_home else game.home_score
        opponent_id = game.away_team_id if is_home else game.home_team_id
        margin = None
        result = "—"
        if team_score is not None and opponent_score is not None:
            margin = team_score - opponent_score
            result = "W" if margin > 0 else "L"
            recent_wins += 1 if margin > 0 else 0
            recent_count += 1
            recent_margin_total += margin

        recent_games.append(
            TeamRecentGame(
                game_id=game.game_id,
                game_date=game.game_date.isoformat() if game.game_date else None,
                opponent_abbreviation=team_lookup.get(opponent_id),
                is_home=is_home,
                result=result,
                team_score=team_score,
                opponent_score=opponent_score,
                margin=margin,
            )
        )

    for game in completed_games:
        is_home = game.home_team_id == team.id
        team_score = game.home_score if is_home else game.away_score
        opponent_score = game.away_score if is_home else game.home_score
        if team_score is None or opponent_score is None:
            continue
        total_team_points += team_score
        total_opp_points += opponent_score
        result = "W" if team_score > opponent_score else "L"
        if result == "W":
            total_wins += 1
        else:
            total_losses += 1

    for game in team_games:
        is_home = game.home_team_id == team.id
        team_score = game.home_score if is_home else game.away_score
        opponent_score = game.away_score if is_home else game.home_score
        if team_score is None or opponent_score is None:
            continue
        result = "W" if team_score > opponent_score else "L"
        if streak_result is None:
            streak_result = result
            streak_length = 1
        elif result == streak_result:
            streak_length += 1
        else:
            break

    l10_record = None
    if recent_count:
        l10_record = f"{recent_wins}-{recent_count - recent_wins}"

    current_streak = None
    if streak_result and streak_length:
        current_streak = f"{streak_result}{streak_length}"

    impact_leaders = []
    player_map = {player.id: player for player in roster_players}
    for row in on_off_rows[:5]:
        player = player_map.get(row.player_id)
        season_row = season_map.get(row.player_id)
        if not player:
            continue
        impact_leaders.append(
            TeamImpactLeader(
                player_id=player.id,
                player_name=player.full_name,
                team_abbreviation=team.abbreviation,
                on_off_net=row.on_off_net,
                on_minutes=row.on_minutes,
                bpm=season_row.bpm if season_row else None,
                pts_pg=season_row.pts_pg if season_row else None,
                clutch_pts=season_row.clutch_pts if season_row else None,
            )
        )

    lineup_rows = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.team_id == team.id,
            LineupStats.net_rating.isnot(None),
            LineupStats.possessions.isnot(None),
            LineupStats.possessions >= 20,
        )
        .order_by(LineupStats.net_rating.desc())
        .limit(100)
        .all()
    )
    best_lineups = [_serialize_lineup(row, db) for row in lineup_rows[:5]]
    worst_lineups = [_serialize_lineup(row, db) for row in list(reversed(lineup_rows[-5:]))]

    return TeamIntelligenceResponse(
        team_id=team.id,
        abbreviation=team.abbreviation,
        name=team.name,
        season=season,
        conference=None,
        playoff_rank=None,
        wins=total_wins if completed_games else None,
        losses=total_losses if completed_games else None,
        win_pct=(total_wins / len(completed_games)) if completed_games else None,
        l10=l10_record,
        current_streak=current_streak,
        pts_pg=(total_team_points / len(completed_games)) if completed_games else None,
        opp_pts_pg=(total_opp_points / len(completed_games)) if completed_games else None,
        diff_pts_pg=((total_team_points - total_opp_points) / len(completed_games)) if completed_games else None,
        recent_record=l10_record,
        recent_avg_margin=(recent_margin_total / recent_count) if recent_count else None,
        pbp_coverage=TeamPbpCoverage(
            season=season,
            eligible_games=eligible_games,
            synced_games=synced_games,
            players_with_on_off=players_with_on_off,
            players_with_scoring_splits=players_with_scoring_splits,
            status=coverage_status,
        ),
        impact_leaders=impact_leaders,
        best_lineups=best_lineups,
        worst_lineups=worst_lineups,
        recent_games=recent_games,
    )


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
