from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from db.models import GamePlayerStat, Player, PlayerOnOff, SeasonStat, Team, WarehouseGame
from models.team import TeamImpactLeader, TeamRotationGame, TeamRotationPlayerRow, TeamRotationReport


WINDOW_SIZE = 10
MINUTE_SHIFT_NOTE_THRESHOLD = 4.0


def _empty_report(team: Team, season: str, status: str = "limited") -> TeamRotationReport:
    return TeamRotationReport(
        team_id=team.id,
        abbreviation=team.abbreviation,
        season=season,
        status=status,
        window_games=0,
        starter_stability="stable",
        recent_starters=[],
        minute_load_leaders=[],
        rotation_risers=[],
        rotation_fallers=[],
        on_off_anchors=[],
        recommended_games=[],
    )


def _round_minutes(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(value, 1)


def _is_modern_rotation_season(season: str) -> bool:
    try:
        return int(season[:4]) >= 2024
    except (TypeError, ValueError):
        return False


def _starter_stability(unique_starters: int) -> str:
    if unique_starters <= 5:
        return "stable"
    if unique_starters <= 7:
        return "mixed"
    return "volatile"


def _player_row(
    player_id: int,
    player_name: str,
    team_abbreviation: str,
    starts_last_10: int,
    avg_minutes_last_10: Optional[float],
    avg_minutes_season: Optional[float],
    is_primary_starter: bool,
) -> TeamRotationPlayerRow:
    minutes_delta = None
    if avg_minutes_last_10 is not None and avg_minutes_season is not None:
        minutes_delta = round(avg_minutes_last_10 - avg_minutes_season, 1)

    return TeamRotationPlayerRow(
        player_id=player_id,
        player_name=player_name,
        team_abbreviation=team_abbreviation,
        starts_last_10=starts_last_10,
        avg_minutes_last_10=_round_minutes(avg_minutes_last_10),
        avg_minutes_season=_round_minutes(avg_minutes_season),
        minutes_delta=minutes_delta,
        is_primary_starter=is_primary_starter,
    )


def build_team_rotation_report(db: Session, team: Team, season: str) -> TeamRotationReport:
    if not _is_modern_rotation_season(season):
        return _empty_report(team, season)

    recent_games = (
        db.query(WarehouseGame)
        .filter(
            WarehouseGame.season == season,
            (WarehouseGame.home_team_id == team.id) | (WarehouseGame.away_team_id == team.id),
            WarehouseGame.home_score.isnot(None),
            WarehouseGame.away_score.isnot(None),
        )
        .order_by(WarehouseGame.game_date.desc().nullslast(), WarehouseGame.game_id.desc())
        .limit(WINDOW_SIZE)
        .all()
    )

    if not recent_games:
        return _empty_report(team, season, status="ready")

    game_ids = [game.game_id for game in recent_games]
    game_player_rows = (
        db.query(GamePlayerStat)
        .filter(
            GamePlayerStat.season == season,
            GamePlayerStat.team_id == team.id,
            GamePlayerStat.game_id.in_(game_ids),
        )
        .all()
    )

    if not game_player_rows:
        return _empty_report(team, season)

    season_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.team_abbreviation == team.abbreviation,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    season_map = {row.player_id: row for row in season_rows}

    player_ids = sorted(
        set(list(season_map.keys()) + [row.player_id for row in game_player_rows])
    )
    players = db.query(Player).filter(Player.id.in_(player_ids) if player_ids else False).all() if player_ids else []
    player_map = {player.id: player for player in players}

    player_recent_minutes = dict((player_id, 0.0) for player_id in player_ids)
    player_recent_starts = dict((player_id, 0) for player_id in player_ids)
    player_game_map = dict((player_id, {}) for player_id in player_ids)
    unique_starters = set()

    for row in game_player_rows:
        player_recent_minutes[row.player_id] = player_recent_minutes.get(row.player_id, 0.0) + float(row.min or 0.0)
        if row.is_starter:
            player_recent_starts[row.player_id] = player_recent_starts.get(row.player_id, 0) + 1
            unique_starters.add(row.player_id)
        player_game_map.setdefault(row.player_id, {})[row.game_id] = row

    window_games = len(recent_games)
    player_rows = []
    for player_id in player_ids:
        season_row = season_map.get(player_id)
        player = player_map.get(player_id)
        if not player and not season_row:
            continue

        player_name = player.full_name if player else str(player_id)
        avg_recent = player_recent_minutes.get(player_id, 0.0) / float(window_games)
        avg_season = season_row.min_pg if season_row and season_row.min_pg is not None else 0.0
        starts_last_10 = player_recent_starts.get(player_id, 0)
        is_primary_starter = starts_last_10 >= (window_games / 2.0)

        player_rows.append(
            _player_row(
                player_id=player_id,
                player_name=player_name,
                team_abbreviation=team.abbreviation,
                starts_last_10=starts_last_10,
                avg_minutes_last_10=avg_recent,
                avg_minutes_season=avg_season,
                is_primary_starter=is_primary_starter,
            )
        )

    recent_starters = [
        row for row in player_rows if row.starts_last_10 > 0
    ]
    recent_starters.sort(
        key=lambda row: (
            row.starts_last_10,
            row.avg_minutes_last_10 if row.avg_minutes_last_10 is not None else -1.0,
        ),
        reverse=True,
    )

    minute_load_leaders = sorted(
        player_rows,
        key=lambda row: row.avg_minutes_last_10 if row.avg_minutes_last_10 is not None else -1.0,
        reverse=True,
    )[:8]

    rotation_risers = [
        row for row in player_rows if row.minutes_delta is not None and row.minutes_delta > 0
    ]
    rotation_risers.sort(key=lambda row: row.minutes_delta if row.minutes_delta is not None else -999.0, reverse=True)

    rotation_fallers = [
        row for row in player_rows if row.minutes_delta is not None and row.minutes_delta < 0
    ]
    rotation_fallers.sort(key=lambda row: row.minutes_delta if row.minutes_delta is not None else 999.0)

    on_off_rows = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.player_id.in_(player_ids) if player_ids else False,
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
            PlayerOnOff.on_off_net.isnot(None),
        )
        .order_by(PlayerOnOff.on_off_net.desc(), PlayerOnOff.on_minutes.desc().nullslast())
        .limit(8)
        .all()
    ) if player_ids else []

    on_off_anchors = []
    for row in on_off_rows:
        player = player_map.get(row.player_id)
        season_row = season_map.get(row.player_id)
        if not player:
            continue
        on_off_anchors.append(
            TeamImpactLeader(
                player_id=player.id,
                player_name=player.full_name,
                team_abbreviation=team.abbreviation,
                on_off_net=row.on_off_net,
                on_minutes=row.on_minutes,
                bpm=season_row.bpm if season_row else None,
                pts_pg=season_row.pts_pg if season_row else None,
                clutch_pts=None,
            )
        )

    recommended_games = _build_recommended_games(
        team=team,
        recent_games=recent_games,
        player_rows=player_rows,
        player_game_map=player_game_map,
    )

    return TeamRotationReport(
        team_id=team.id,
        abbreviation=team.abbreviation,
        season=season,
        status="ready",
        window_games=window_games,
        starter_stability=_starter_stability(len(unique_starters)),
        recent_starters=recent_starters,
        minute_load_leaders=minute_load_leaders,
        rotation_risers=rotation_risers[:5],
        rotation_fallers=rotation_fallers[:5],
        on_off_anchors=on_off_anchors[:5],
        recommended_games=recommended_games,
    )


def _build_recommended_games(
    team: Team,
    recent_games: Sequence[WarehouseGame],
    player_rows: Sequence[TeamRotationPlayerRow],
    player_game_map: Dict[int, Dict[str, GamePlayerStat]],
) -> List[TeamRotationGame]:
    player_row_map = dict((row.player_id, row) for row in player_rows)
    scored_games: List[Tuple[float, int, TeamRotationGame]] = []

    for index, game in enumerate(recent_games):
        is_home = game.home_team_id == team.id
        team_score = game.home_score if is_home else game.away_score
        opponent_score = game.away_score if is_home else game.home_score
        if team_score is None or opponent_score is None:
            continue

        margin = team_score - opponent_score
        deviations = []
        unusual_starters = 0

        for player_id, player_row in player_row_map.items():
            game_row = player_game_map.get(player_id, {}).get(game.game_id)
            game_minutes = float(game_row.min or 0.0) if game_row else 0.0
            season_minutes = player_row.avg_minutes_season or 0.0
            delta = round(game_minutes - season_minutes, 1)
            if abs(delta) >= MINUTE_SHIFT_NOTE_THRESHOLD:
                deviations.append((abs(delta), player_row.player_name, delta))
            if game_row and game_row.is_starter and not player_row.is_primary_starter:
                unusual_starters += 1

        deviations = sorted(deviations, key=lambda item: item[0], reverse=True)
        rotation_score = sum(item[0] for item in deviations[:3]) + (unusual_starters * 3.0) + abs(float(margin))
        note = _rotation_note(deviations, unusual_starters, margin)
        opponent_abbreviation = game.away_team_abbreviation if is_home else game.home_team_abbreviation
        result = "W" if margin > 0 else "L"

        scored_games.append(
            (
                rotation_score,
                index,
                TeamRotationGame(
                    game_id=game.game_id,
                    game_date=game.game_date.isoformat() if game.game_date else None,
                    opponent_abbreviation=opponent_abbreviation,
                    result=result,
                    team_score=team_score,
                    opponent_score=opponent_score,
                    rotation_note=note,
                ),
            )
        )

    scored_games.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    return [item[2] for item in scored_games[:5]]


def _rotation_note(
    deviations: Sequence[Tuple[float, str, float]],
    unusual_starters: int,
    margin: int,
) -> str:
    note_parts = []

    if unusual_starters:
        label = "non-core starter" if unusual_starters == 1 else "non-core starters"
        note_parts.append("%s %s" % (unusual_starters, label))

    if deviations:
        shift_parts = []
        for _, player_name, delta in deviations[:2]:
            shift_parts.append("%s %s min vs season" % (player_name, _signed(delta)))
        note_parts.append(", ".join(shift_parts))

    if not note_parts:
        return "Final margin swung %s points." % abs(margin)

    return "; ".join(note_parts) + "."


def _signed(value: float) -> str:
    return ("%+.1f" % value)
