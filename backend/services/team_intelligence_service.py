from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from db.models import (
    GameLog,
    LineupStats,
    PlayByPlay,
    PlayByPlayEvent,
    Player,
    PlayerOnOff,
    SeasonStat,
    Team,
    TeamStanding,
    WarehouseGame,
)
from models.team import TeamImpactLeader, TeamIntelligenceResponse, TeamPbpCoverage, TeamRecentGame


def _is_modern_warehouse_season(season: str) -> bool:
    try:
        return int(season[:4]) >= 2024
    except (TypeError, ValueError):
        return False


def _serialize_lineup(row: LineupStats, db: Session) -> dict:
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


def _pick_season_rows(
    rows: List[SeasonStat],
    team_abbreviation: str,
) -> Dict[int, SeasonStat]:
    best: Dict[int, SeasonStat] = {}
    for row in rows:
        current = best.get(row.player_id)
        candidate_rank = (
            1 if row.team_abbreviation == team_abbreviation else 0,
            row.gp or 0,
            row.pts_pg or 0.0,
        )
        if current is None:
            best[row.player_id] = row
            continue
        current_rank = (
            1 if current.team_abbreviation == team_abbreviation else 0,
            current.gp or 0,
            current.pts_pg or 0.0,
        )
        if candidate_rank > current_rank:
            best[row.player_id] = row
    return best


def _recent_record_string(wins: int, games: int) -> Optional[str]:
    if games <= 0:
        return None
    return "{0}-{1}".format(wins, games - wins)


def _standing_record(standing: Optional[TeamStanding]) -> Tuple[Optional[int], Optional[int], Optional[float]]:
    if standing is None:
        return None, None, None
    wins = standing.wins or 0
    losses = standing.losses or 0
    total = wins + losses
    return wins, losses, (wins / total) if total else None


def _standing_l10(standing: Optional[TeamStanding]) -> Optional[str]:
    if standing is None:
        return None
    return "{0}-{1}".format(standing.last_10_wins or 0, standing.last_10_losses or 0)


def _standing_streak(standing: Optional[TeamStanding]) -> Optional[str]:
    if standing is None or not standing.streak_type or not standing.current_streak:
        return None
    return "{0}{1}".format(standing.streak_type, abs(int(standing.current_streak)))


def _team_games_modern(db: Session, team: Team, season: str) -> List[WarehouseGame]:
    return (
        db.query(WarehouseGame)
        .filter(
            WarehouseGame.season == season,
            or_(WarehouseGame.home_team_id == team.id, WarehouseGame.away_team_id == team.id),
        )
        .order_by(WarehouseGame.game_date.desc().nullslast(), WarehouseGame.game_id.desc())
        .all()
    )


def _team_games_legacy(db: Session, team: Team, season: str) -> List[GameLog]:
    return (
        db.query(GameLog)
        .filter(
            GameLog.season == season,
            or_(GameLog.home_team_id == team.id, GameLog.away_team_id == team.id),
        )
        .order_by(GameLog.game_date.desc().nullslast(), GameLog.game_id.desc())
        .all()
    )


def _build_recent_games_modern(team: Team, games: List[WarehouseGame]) -> Tuple[List[TeamRecentGame], int, int, float]:
    recent_games: List[TeamRecentGame] = []
    recent_wins = 0
    recent_count = 0
    recent_margin_total = 0.0
    for game in games[:10]:
        is_home = game.home_team_id == team.id
        team_score = game.home_score if is_home else game.away_score
        opponent_score = game.away_score if is_home else game.home_score
        opponent_abbreviation = game.away_team_abbreviation if is_home else game.home_team_abbreviation
        margin = None
        result = "—"
        if team_score is not None and opponent_score is not None:
            margin = team_score - opponent_score
            result = "W" if margin > 0 else "L"
            if margin > 0:
                recent_wins += 1
            recent_count += 1
            recent_margin_total += margin
        recent_games.append(
            TeamRecentGame(
                game_id=game.game_id,
                game_date=game.game_date.isoformat() if game.game_date else None,
                opponent_abbreviation=opponent_abbreviation,
                is_home=is_home,
                result=result,
                team_score=team_score,
                opponent_score=opponent_score,
                margin=margin,
            )
        )
    return recent_games, recent_wins, recent_count, recent_margin_total


def _build_recent_games_legacy(db: Session, team: Team, games: List[GameLog]) -> Tuple[List[TeamRecentGame], int, int, float]:
    recent_games: List[TeamRecentGame] = []
    recent_wins = 0
    recent_count = 0
    recent_margin_total = 0.0
    team_lookup = (
        {
            t.id: t.abbreviation
            for t in db.query(Team)
            .filter(
                Team.id.in_([game.home_team_id for game in games] + [game.away_team_id for game in games])
            )
            .all()
        }
        if games
        else {}
    )
    for game in games[:10]:
        is_home = game.home_team_id == team.id
        team_score = game.home_score if is_home else game.away_score
        opponent_score = game.away_score if is_home else game.home_score
        opponent_id = game.away_team_id if is_home else game.home_team_id
        margin = None
        result = "—"
        if team_score is not None and opponent_score is not None:
            margin = team_score - opponent_score
            result = "W" if margin > 0 else "L"
            if margin > 0:
                recent_wins += 1
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
    return recent_games, recent_wins, recent_count, recent_margin_total


def _build_totals_modern(team: Team, games: List[WarehouseGame]) -> Tuple[int, int, int, int]:
    total_wins = 0
    total_losses = 0
    total_team_points = 0
    total_opp_points = 0
    for game in games:
        is_home = game.home_team_id == team.id
        team_score = game.home_score if is_home else game.away_score
        opponent_score = game.away_score if is_home else game.home_score
        if team_score is None or opponent_score is None:
            continue
        total_team_points += team_score
        total_opp_points += opponent_score
        if team_score > opponent_score:
            total_wins += 1
        else:
            total_losses += 1
    return total_wins, total_losses, total_team_points, total_opp_points


def _current_streak_modern(team: Team, games: List[WarehouseGame]) -> Optional[str]:
    streak_result: Optional[str] = None
    streak_length = 0
    for game in games:
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
    if streak_result is None or streak_length == 0:
        return None
    return "{0}{1}".format(streak_result, streak_length)


def _latest_standing(db: Session, team_id: int, season: str) -> Optional[TeamStanding]:
    return (
        db.query(TeamStanding)
        .filter(TeamStanding.team_id == team_id, TeamStanding.season == season)
        .order_by(TeamStanding.snapshot_date.desc(), TeamStanding.updated_at.desc())
        .first()
    )


def _conference_rank(db: Session, standing: Optional[TeamStanding], season: str) -> Optional[int]:
    if standing is None or not standing.conference:
        return None
    latest_snapshot = (
        db.query(func.max(TeamStanding.snapshot_date))
        .filter(TeamStanding.season == season)
        .scalar()
    )
    if latest_snapshot is None:
        return None
    conf_rows = (
        db.query(TeamStanding)
        .filter(
            TeamStanding.season == season,
            TeamStanding.snapshot_date == latest_snapshot,
            TeamStanding.conference == standing.conference,
        )
        .all()
    )
    conf_rows.sort(key=lambda row: (-(row.wins or 0), row.losses or 0, row.team_id))
    for rank, row in enumerate(conf_rows, start=1):
        if row.team_id == standing.team_id:
            return rank
    return None


def build_team_intelligence(db: Session, abbr: str, season: str) -> TeamIntelligenceResponse:
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
    modern = _is_modern_warehouse_season(season)

    if modern:
        team_games = _team_games_modern(db, team, season)
        eligible_games = len(team_games)
        team_game_ids = [game.game_id for game in team_games]
        synced_games = 0
        if team_game_ids:
            synced_games = (
                db.query(func.count(func.distinct(PlayByPlayEvent.game_id)))
                .filter(PlayByPlayEvent.game_id.in_(team_game_ids))
                .scalar()
                or 0
            )
        recent_games, recent_wins, recent_count, recent_margin_total = _build_recent_games_modern(team, team_games)
        total_wins, total_losses, total_team_points, total_opp_points = _build_totals_modern(team, team_games)
        current_streak = _current_streak_modern(team, team_games)
        canonical_source = "warehouse"
    else:
        team_games = _team_games_legacy(db, team, season)
        eligible_games = len(team_games)
        team_game_ids = [game.game_id for game in team_games]
        synced_games = 0
        if team_game_ids:
            synced_games = (
                db.query(func.count(func.distinct(PlayByPlay.game_id)))
                .filter(PlayByPlay.game_id.in_(team_game_ids))
                .scalar()
                or 0
            )
        recent_games, recent_wins, recent_count, recent_margin_total = _build_recent_games_legacy(db, team, team_games)
        total_wins, total_losses, total_team_points, total_opp_points = _build_totals_modern(team, team_games)  # type: ignore[arg-type]
        current_streak = _current_streak_modern(team, team_games)  # type: ignore[arg-type]
        canonical_source = "legacy-plus-derived"

    season_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id.in_(player_ids) if player_ids else False,
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
        if player_ids
        else []
    )
    season_map = _pick_season_rows(season_rows, team.abbreviation)

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
        if player_ids
        else []
    )
    players_with_on_off = len(on_off_rows)
    players_with_scoring_splits = sum(
        1
        for row in season_rows
        if any(
            value is not None
            for value in [row.clutch_pts, row.clutch_fg_pct, row.second_chance_pts, row.fast_break_pts]
        )
    )

    if modern:
        if eligible_games == 0 and not season_rows:
            data_status = "missing"
        elif synced_games >= eligible_games and eligible_games > 0:
            data_status = "ready"
        else:
            data_status = "partial"
    else:
        data_status = "limited" if (eligible_games > 0 or season_rows or on_off_rows) else "missing"

    if synced_games == 0 and players_with_on_off == 0 and players_with_scoring_splits == 0:
        coverage_status = "none"
    elif eligible_games > 0 and synced_games >= eligible_games and players_with_on_off >= max(1, len(player_ids) // 3):
        coverage_status = "ready"
    else:
        coverage_status = "partial"

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

    impact_leaders: List[TeamImpactLeader] = []
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

    standing = _latest_standing(db, team.id, season)
    standing_wins, standing_losses, standing_win_pct = _standing_record(standing)

    timestamps: List[datetime] = []
    if modern:
        timestamps.extend(
            row.updated_at
            for row in team_games
            if getattr(row, "updated_at", None) is not None
        )
    if standing and standing.updated_at:
        timestamps.append(standing.updated_at)
    timestamps.extend(row.updated_at for row in on_off_rows if row.updated_at is not None)
    timestamps.extend(row.updated_at for row in season_rows if row.updated_at is not None)
    timestamps.extend(row.updated_at for row in lineup_rows if row.updated_at is not None)
    last_synced_at = max(timestamps).isoformat() if timestamps else None

    completed_games = total_wins + total_losses
    wins = standing_wins if standing_wins is not None else (total_wins if completed_games else None)
    losses = standing_losses if standing_losses is not None else (total_losses if completed_games else None)
    win_pct = standing_win_pct if standing_win_pct is not None else ((total_wins / completed_games) if completed_games else None)

    return TeamIntelligenceResponse(
        team_id=team.id,
        abbreviation=team.abbreviation,
        name=team.name,
        season=season,
        data_status=data_status,
        canonical_source=canonical_source,
        last_synced_at=last_synced_at,
        conference=standing.conference if standing else None,
        playoff_rank=_conference_rank(db, standing, season),
        wins=wins,
        losses=losses,
        win_pct=win_pct,
        l10=_standing_l10(standing) or _recent_record_string(recent_wins, recent_count),
        current_streak=_standing_streak(standing) or current_streak,
        pts_pg=(total_team_points / completed_games) if completed_games else None,
        opp_pts_pg=(total_opp_points / completed_games) if completed_games else None,
        diff_pts_pg=((total_team_points - total_opp_points) / completed_games) if completed_games else None,
        recent_record=_recent_record_string(recent_wins, recent_count),
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
