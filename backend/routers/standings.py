from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import GameTeamStat, Team, TeamSeasonStat, TeamStanding, WarehouseGame
from models.standings import StandingsEntry, StandingsHistoryResponse
from services.standings_service import get_standings_history
from services.standings_service import TEAM_CONF_DIV

router = APIRouter()


def _standings_from_db(season: str, db: Session) -> Optional[List[StandingsEntry]]:
    """Return materialized standings from team_standings table, or None if empty.

    Uses the most recent snapshot per team so the table's daily history rows
    don't produce duplicate entries.
    """
    # Subquery: latest snapshot_date per team for this season
    latest_sq = (
        db.query(
            TeamStanding.team_id,
            func.max(TeamStanding.snapshot_date).label("latest_date"),
        )
        .filter(TeamStanding.season == season)
        .group_by(TeamStanding.team_id)
        .subquery()
    )

    rows = (
        db.query(TeamStanding, Team)
        .join(Team, Team.id == TeamStanding.team_id)
        .join(
            latest_sq,
            (TeamStanding.team_id == latest_sq.c.team_id)
            & (TeamStanding.snapshot_date == latest_sq.c.latest_date),
        )
        .filter(TeamStanding.season == season)
        .all()
    )
    if not rows:
        return None

    # Rebuild the full StandingsEntry shape from the materialized table.
    entries: List[dict] = []
    for standing, team in rows:
        streak_str = ""
        if standing.streak_type:
            streak_count = abs(standing.current_streak or 0)
            streak_str = f"{standing.streak_type}{streak_count}"

        wins = standing.wins or 0
        losses = standing.losses or 0
        gp = wins + losses

        entries.append({
            "team_id": team.id,
            "team_city": team.city or "",
            "team_name": team.name or "",
            "conference": standing.conference or "",
            "division": standing.division or "",
            "playoff_rank": 0,
            "wins": wins,
            "losses": losses,
            "win_pct": wins / gp if gp > 0 else 0.0,
            "games_back": None,
            "l10": f"{standing.last_10_wins or 0}-{standing.last_10_losses or 0}",
            "home_record": f"{standing.home_wins or 0}-{standing.home_losses or 0}",
            "road_record": f"{standing.road_wins or 0}-{standing.road_losses or 0}",
            "pts_pg": None,
            "opp_pts_pg": None,
            "diff_pts_pg": None,
            "current_streak": streak_str,
            "clinch_indicator": None,
            "abbreviation": team.abbreviation,
        })

    # Assign playoff_rank and games_back within each conference
    for conf in ("East", "West"):
        conf_entries = [e for e in entries if e["conference"] == conf]
        conf_entries.sort(key=lambda e: (-e["wins"], e["losses"]))
        if not conf_entries:
            continue
        leader_w = conf_entries[0]["wins"]
        leader_l = conf_entries[0]["losses"]
        for rank, e in enumerate(conf_entries, start=1):
            e["playoff_rank"] = rank
            e["games_back"] = 0.0 if rank == 1 else ((leader_w - e["wins"]) + (e["losses"] - leader_l)) / 2.0

    return [StandingsEntry(**e) for e in entries]


def _team_display_parts(team: Team) -> tuple[str, str]:
    """Avoid duplicate/blank names when official rows only carry full team names."""
    city = (team.city or "").strip()
    name = (team.name or "").strip()
    if city and name.startswith(f"{city} "):
        return "", name
    return city, name


def _team_game_context(season: str, db: Session) -> dict[int, dict]:
    rows = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(
            GameTeamStat.season == season,
            GameTeamStat.won.isnot(None),
            WarehouseGame.game_date.isnot(None),
            WarehouseGame.status == "final",
        )
        .order_by(WarehouseGame.game_date.desc(), WarehouseGame.game_id.desc())
        .all()
    )

    games_by_team: dict[int, list[dict]] = {}
    for team_stat, game in rows:
        is_home = bool(team_stat.is_home)
        opponent_abbreviation = (
            game.away_team_abbreviation if is_home else game.home_team_abbreviation
        )
        opponent_score = game.away_score if is_home else game.home_score
        margin = None
        if team_stat.pts is not None and opponent_score is not None:
            margin = int(team_stat.pts or 0) - int(opponent_score or 0)

        games_by_team.setdefault(team_stat.team_id, []).append({
            "game_date": game.game_date,
            "game_id": game.game_id,
            "won": bool(team_stat.won),
            "is_home": is_home,
            "margin": margin,
            "opponent_abbreviation": opponent_abbreviation,
        })

    context: dict[int, dict] = {}
    for team_id, games in games_by_team.items():
        home_games = [game for game in games if game["is_home"]]
        road_games = [game for game in games if not game["is_home"]]
        last10 = games[:10]
        trend_games = list(reversed(last10))
        margins = [game["margin"] for game in trend_games if game["margin"] is not None]
        avg_margin = round(sum(margins) / len(margins), 1) if margins else 0.0
        direction = "positive" if avg_margin > 0 else "negative" if avg_margin < 0 else "flat"

        streak_type = ""
        streak_count = 0
        for game in games:
            current = "W" if game["won"] else "L"
            if not streak_type:
                streak_type = current
                streak_count = 1
            elif current == streak_type:
                streak_count += 1
            else:
                break

        context[team_id] = {
            "l10": f"{sum(1 for game in last10 if game['won'])}-{sum(1 for game in last10 if not game['won'])}" if last10 else "—",
            "home_record": f"{sum(1 for game in home_games if game['won'])}-{sum(1 for game in home_games if not game['won'])}" if home_games else "—",
            "road_record": f"{sum(1 for game in road_games if game['won'])}-{sum(1 for game in road_games if not game['won'])}" if road_games else "—",
            "current_streak": f"{streak_type}{streak_count}" if streak_type else "",
            "recent_trend": {
                "games": [
                    {
                        "date": game["game_date"].isoformat(),
                        "won": game["won"],
                        "margin": game["margin"] if game["margin"] is not None else 0,
                        "is_home": game["is_home"],
                        "opponent_abbreviation": game["opponent_abbreviation"],
                    }
                    for game in trend_games
                ],
                "last_10_record": f"{sum(1 for game in last10 if game['won'])}-{sum(1 for game in last10 if not game['won'])}" if last10 else "—",
                "avg_margin": avg_margin,
                "direction": direction,
            } if trend_games else None,
        }

    return context


def _official_stat_payload(team_stats: TeamSeasonStat) -> dict:
    opp_pts_pg = None
    if team_stats.pts_pg is not None and team_stats.plus_minus_pg is not None:
        opp_pts_pg = team_stats.pts_pg - team_stats.plus_minus_pg

    return {
        "gp": team_stats.gp,
        "pts_pg": team_stats.pts_pg,
        "opp_pts_pg": opp_pts_pg,
        "diff_pts_pg": team_stats.plus_minus_pg,
        "reb_pg": team_stats.reb_pg,
        "ast_pg": team_stats.ast_pg,
        "tov_pg": team_stats.tov_pg,
        "stl_pg": team_stats.stl_pg,
        "blk_pg": team_stats.blk_pg,
        "fg_pct": team_stats.fg_pct,
        "fg3_pct": team_stats.fg3_pct,
        "ft_pct": team_stats.ft_pct,
        "plus_minus_pg": team_stats.plus_minus_pg,
        "off_rating": team_stats.off_rating,
        "def_rating": team_stats.def_rating,
        "net_rating": team_stats.net_rating,
        "pace": team_stats.pace,
        "efg_pct": team_stats.efg_pct,
        "ts_pct": team_stats.ts_pct,
        "pie": team_stats.pie,
        "oreb_pct": team_stats.oreb_pct,
        "dreb_pct": team_stats.dreb_pct,
        "tov_pct": team_stats.tov_pct,
        "ast_pct": team_stats.ast_pct,
        "off_rating_rank": team_stats.off_rating_rank,
        "def_rating_rank": team_stats.def_rating_rank,
        "net_rating_rank": team_stats.net_rating_rank,
        "pace_rank": team_stats.pace_rank,
        "efg_pct_rank": team_stats.efg_pct_rank,
        "ts_pct_rank": team_stats.ts_pct_rank,
        "oreb_pct_rank": team_stats.oreb_pct_rank,
        "tov_pct_rank": team_stats.tov_pct_rank,
    }


def _standings_from_team_season_stats(season: str, db: Session) -> Optional[List[StandingsEntry]]:
    """Fallback for current seasons before daily standings snapshots exist."""
    rows = (
        db.query(TeamSeasonStat, Team)
        .join(Team, Team.id == TeamSeasonStat.team_id)
        .filter(
            TeamSeasonStat.season == season,
            TeamSeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    if not rows:
        return None

    game_context = _team_game_context(season, db)
    entries: List[dict] = []
    for team_stats, team in rows:
        abbr = team.abbreviation or ""
        fallback = TEAM_CONF_DIV.get(abbr, {})
        conference = (team.conference or fallback.get("conference") or "").strip()
        division = (team.division or fallback.get("division") or "").strip()
        team_city, team_name = _team_display_parts(team)
        wins = team_stats.w or 0
        losses = team_stats.l or 0
        gp = wins + losses
        context = game_context.get(team.id, {})

        entries.append({
            "team_id": team.id,
            "team_city": team_city,
            "team_name": team_name,
            "conference": conference,
            "division": division,
            "playoff_rank": 0,
            "wins": wins,
            "losses": losses,
            "win_pct": team_stats.w_pct if team_stats.w_pct is not None else (wins / gp if gp else 0.0),
            "games_back": None,
            "l10": context.get("l10", "—"),
            "home_record": context.get("home_record", "—"),
            "road_record": context.get("road_record", "—"),
            "current_streak": context.get("current_streak", ""),
            "recent_trend": context.get("recent_trend"),
            "clinch_indicator": None,
            "abbreviation": abbr,
            **_official_stat_payload(team_stats),
        })

    for conf in ("East", "West"):
        conf_entries = [e for e in entries if e["conference"] == conf]
        conf_entries.sort(key=lambda e: (-e["wins"], e["losses"]))
        if not conf_entries:
            continue
        leader_w = conf_entries[0]["wins"]
        leader_l = conf_entries[0]["losses"]
        for rank, e in enumerate(conf_entries, start=1):
            e["playoff_rank"] = rank
            e["games_back"] = 0.0 if rank == 1 else ((leader_w - e["wins"]) + (e["losses"] - leader_l)) / 2.0

    return [StandingsEntry(**e) for e in entries]


@router.get("/history", response_model=List[StandingsHistoryResponse])
def get_standings_history_endpoint(
    season: str = Query("2024-25"),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Return per-team win-pct time series for the last N days."""
    return get_standings_history(season, days, db)


@router.get("", response_model=List[StandingsEntry])
def get_standings(
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return league standings from snapshots, or official team stats when snapshots are absent."""
    snapshot_entries = _standings_from_db(season, db)
    official_entries = _standings_from_team_season_stats(season, db)
    entries = official_entries or snapshot_entries
    if entries is None:
        return []

    entries.sort(key=lambda e: (e.conference, e.playoff_rank))
    return entries
