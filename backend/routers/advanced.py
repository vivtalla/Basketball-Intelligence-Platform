"""Advanced stats endpoints: on/off splits, clutch stats, lineup analysis."""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import PlayerGameLog, PlayerOnOff, SeasonStat, LineupStats, Player, Team, GameLog, PlayByPlay
from models.stats import (
    PbpCoverage,
    PbpCoverageDashboard,
    PbpCoveragePlayerRow,
    PbpCoverageSeasonSummary,
    PbpCoverageTeamRow,
)
from services.pbp_sync_service import sync_pbp_for_player, sync_pbp_for_season
from services.sync_service import sync_player_if_needed

router = APIRouter()


def _build_pbp_dashboard(db: Session, season: str) -> PbpCoverageDashboard:
    """Assemble a league-wide snapshot of team/player play-by-play sync coverage."""
    raw_season_rows = (
        db.query(SeasonStat, Player, Team)
        .join(Player, SeasonStat.player_id == Player.id)
        .outerjoin(Team, Player.team_id == Team.id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            Player.is_active == True,  # noqa: E712
        )
        .all()
    )
    season_rows_by_player: dict[int, tuple[SeasonStat, Player, Team | None]] = {}
    for season_row, player, team in raw_season_rows:
        current = season_rows_by_player.get(player.id)
        if current is None:
            season_rows_by_player[player.id] = (season_row, player, team)
            continue

        current_row = current[0]
        preferred_team_abbr = team.abbreviation if team else None
        current_matches_team = preferred_team_abbr and current_row.team_abbreviation == preferred_team_abbr
        incoming_matches_team = preferred_team_abbr and season_row.team_abbreviation == preferred_team_abbr

        if incoming_matches_team and not current_matches_team:
            season_rows_by_player[player.id] = (season_row, player, team)
        elif incoming_matches_team == current_matches_team:
            current_gp = current_row.gp or 0
            incoming_gp = season_row.gp or 0
            if incoming_gp > current_gp:
                season_rows_by_player[player.id] = (season_row, player, team)

    season_rows = list(season_rows_by_player.values())

    on_off_rows = {
        row.player_id: row
        for row in db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
        )
        .all()
    }

    synced_games_by_team = {
        team_id: synced_games
        for team_id, synced_games in (
            db.query(GameLog.home_team_id.label("team_id"), func.count(func.distinct(PlayByPlay.game_id)))
            .join(PlayByPlay, PlayByPlay.game_id == GameLog.game_id)
            .filter(GameLog.season == season)
            .group_by(GameLog.home_team_id)
            .all()
        )
        if team_id is not None
    }
    away_synced_games = (
        db.query(GameLog.away_team_id.label("team_id"), func.count(func.distinct(PlayByPlay.game_id)))
        .join(PlayByPlay, PlayByPlay.game_id == GameLog.game_id)
        .filter(GameLog.season == season)
        .group_by(GameLog.away_team_id)
        .all()
    )
    for team_id, synced_games in away_synced_games:
        if team_id is not None:
            synced_games_by_team[team_id] = max(synced_games_by_team.get(team_id, 0), synced_games)

    eligible_games_by_team = {}
    for team_id, eligible_games in (
        db.query(GameLog.home_team_id.label("team_id"), func.count(GameLog.game_id))
        .filter(GameLog.season == season)
        .group_by(GameLog.home_team_id)
        .all()
    ):
        if team_id is not None:
            eligible_games_by_team[team_id] = eligible_games
    for team_id, eligible_games in (
        db.query(GameLog.away_team_id.label("team_id"), func.count(GameLog.game_id))
        .filter(GameLog.season == season)
        .group_by(GameLog.away_team_id)
        .all()
    ):
        if team_id is not None:
            eligible_games_by_team[team_id] = max(eligible_games_by_team.get(team_id, 0), eligible_games)

    player_rows: list[PbpCoveragePlayerRow] = []
    team_rollups: dict[int, dict] = {}

    for season_row, player, team in season_rows:
        team_id = team.id if team else None
        team_name = team.name if team else "Unassigned"
        team_abbr = team.abbreviation if team else season_row.team_abbreviation or "FA"
        on_off_row = on_off_rows.get(player.id)
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
        eligible_games = season_row.gp or 0
        synced_games = min(eligible_games, eligible_games_by_team.get(team.id if team else None, 0))

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

        player_rows.append(
            PbpCoveragePlayerRow(
                player_id=player.id,
                player_name=player.full_name,
                team_abbreviation=team_abbr,
                season=season,
                eligible_games=eligible_games,
                synced_games=synced_games,
                has_on_off=has_on_off,
                has_scoring_splits=has_scoring_splits,
                status=status,
                last_derived_at=max(timestamps).isoformat() if timestamps else None,
            )
        )

        if team_id is not None and team_id not in team_rollups:
            team_rollups[team_id] = {
                "team_id": team_id,
                "abbreviation": team_abbr,
                "name": team_name,
                "season": season,
                "player_count": 0,
                "players_ready": 0,
                "players_partial": 0,
                "players_none": 0,
                "eligible_games": eligible_games_by_team.get(team.id, 0),
                "synced_games": synced_games_by_team.get(team.id, 0),
            }

        if team_id is not None:
            rollup = team_rollups[team_id]
            rollup["player_count"] += 1
            if status == "ready":
                rollup["players_ready"] += 1
            elif status == "partial":
                rollup["players_partial"] += 1
            else:
                rollup["players_none"] += 1

    team_rows: list[PbpCoverageTeamRow] = []
    for rollup in team_rollups.values():
        if rollup["player_count"] == 0:
            status = "none"
        elif rollup["players_ready"] == rollup["player_count"]:
            status = "ready"
        elif rollup["players_ready"] > 0 or rollup["players_partial"] > 0 or rollup["synced_games"] > 0:
            status = "partial"
        else:
            status = "none"

        team_rows.append(
            PbpCoverageTeamRow(
                **rollup,
                status=status,
            )
        )

    team_rows.sort(key=lambda row: (row.status != "none", row.players_ready, row.synced_games), reverse=True)
    player_rows.sort(
        key=lambda row: (
            row.status == "ready",
            row.status == "partial",
            row.synced_games,
            row.player_name,
        ),
        reverse=True,
    )

    return PbpCoverageDashboard(
        season=season,
        total_teams=len(team_rows),
        total_players=len(player_rows),
        teams_ready=sum(1 for row in team_rows if row.status == "ready"),
        teams_partial=sum(1 for row in team_rows if row.status == "partial"),
        teams_none=sum(1 for row in team_rows if row.status == "none"),
        players_ready=sum(1 for row in player_rows if row.status == "ready"),
        players_partial=sum(1 for row in player_rows if row.status == "partial"),
        players_none=sum(1 for row in player_rows if row.status == "none"),
        eligible_games=sum(row.eligible_games for row in team_rows),
        synced_games=sum(row.synced_games for row in team_rows),
        teams=team_rows,
        players=player_rows[:75],
    )


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

    player_game_ids = [
        r.game_id for r in
        db.query(PlayerGameLog.game_id)
        .filter(
            PlayerGameLog.player_id == player_id,
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
        )
        .all()
    ]

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


@router.get("/pbp-dashboard", response_model=PbpCoverageDashboard)
def get_pbp_dashboard(season: str = "2024-25", db: Session = Depends(get_db)):
    return _build_pbp_dashboard(db, season)


@router.get("/pbp-dashboard-seasons", response_model=List[PbpCoverageSeasonSummary])
def get_pbp_dashboard_season_summaries(db: Session = Depends(get_db)):
    seasons = [
        season
        for season, in db.query(SeasonStat.season)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .distinct()
        .order_by(SeasonStat.season.desc())
        .all()
    ]
    summaries = []
    for season in seasons:
        dashboard = _build_pbp_dashboard(db, season)
        summaries.append(
            PbpCoverageSeasonSummary(
                season=dashboard.season,
                total_teams=dashboard.total_teams,
                total_players=dashboard.total_players,
                teams_ready=dashboard.teams_ready,
                teams_partial=dashboard.teams_partial,
                teams_none=dashboard.teams_none,
                players_ready=dashboard.players_ready,
                players_partial=dashboard.players_partial,
                players_none=dashboard.players_none,
                eligible_games=dashboard.eligible_games,
                synced_games=dashboard.synced_games,
            )
        )
    return summaries


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
