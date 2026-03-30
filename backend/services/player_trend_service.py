from __future__ import annotations

from statistics import pstdev
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from db.models import GamePlayerStat, Player, PlayerGameLog, PlayerOnOff, SeasonStat
from models.player import (
    PlayerTrendForm,
    PlayerTrendGame,
    PlayerTrendImpactSnapshot,
    PlayerTrendReport,
    PlayerTrendSignals,
)


WINDOW_SIZE = 10
MIN_READY_GAMES = 5


def _round_stat(value: Optional[float], digits: int = 1) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _avg(values: Sequence[Optional[float]], digits: int = 1) -> Optional[float]:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / float(len(clean)), digits)


def _build_form(rows: Sequence[PlayerGameLog]) -> PlayerTrendForm:
    return PlayerTrendForm(
        games=len(rows),
        avg_minutes=_avg([row.min for row in rows]),
        avg_points=_avg([row.pts for row in rows]),
        avg_rebounds=_avg([row.reb for row in rows]),
        avg_assists=_avg([row.ast for row in rows]),
        avg_fg_pct=_avg([row.fg_pct for row in rows]),
        avg_fg3_pct=_avg([row.fg3_pct for row in rows]),
        avg_plus_minus=_avg([row.plus_minus for row in rows]),
    )


def _coverage_status(on_off_row: Optional[PlayerOnOff], season_row: Optional[SeasonStat]) -> str:
    has_on_off = bool(on_off_row and on_off_row.on_off_net is not None)
    has_scoring = bool(
        season_row and (
            season_row.clutch_pts is not None
            or season_row.second_chance_pts is not None
            or season_row.fast_break_pts is not None
        )
    )
    if has_on_off and has_scoring:
        return "ready"
    if has_on_off or has_scoring:
        return "partial"
    return "none"


def _minute_volatility(rows: Sequence[PlayerGameLog]) -> Optional[float]:
    clean = [float(row.min) for row in rows if row.min is not None]
    if not clean:
        return None
    if len(clean) == 1:
        return 0.0
    return round(float(pstdev(clean)), 1)


def _role_status(signals: PlayerTrendSignals) -> str:
    minutes_delta = signals.minutes_delta or 0.0
    if signals.starts_last_10 >= 8 and minutes_delta >= -1.0:
        return "entrenched_starter"
    if minutes_delta >= 4.0 or signals.games_30_plus_last_10 >= 5:
        return "rising_rotation"
    if minutes_delta <= -4.0 or signals.games_under_20_last_10 >= 5:
        return "losing_trust"
    if (signals.minute_volatility or 0.0) >= 8.0:
        return "volatile_role"
    return "stable_rotation"


def _trust_signals(
    recent_rows: Sequence[PlayerGameLog],
    season_form: PlayerTrendForm,
    recent_form: PlayerTrendForm,
    starter_map: Dict[str, bool],
) -> PlayerTrendSignals:
    recent_game_count = len(recent_rows)
    starts_last_10 = sum(1 for row in recent_rows if starter_map.get(row.game_id, False))
    minutes = [float(row.min) for row in recent_rows if row.min is not None]
    return PlayerTrendSignals(
        minutes_delta=_round_stat(
            (recent_form.avg_minutes or 0.0) - (season_form.avg_minutes or 0.0)
            if recent_form.avg_minutes is not None and season_form.avg_minutes is not None
            else None
        ),
        points_delta=_round_stat(
            (recent_form.avg_points or 0.0) - (season_form.avg_points or 0.0)
            if recent_form.avg_points is not None and season_form.avg_points is not None
            else None
        ),
        efficiency_delta=_round_stat(
            (recent_form.avg_fg_pct or 0.0) - (season_form.avg_fg_pct or 0.0),
            digits=3,
        ) if recent_form.avg_fg_pct is not None and season_form.avg_fg_pct is not None else None,
        starts_last_10=starts_last_10,
        bench_games_last_10=max(0, recent_game_count - starts_last_10),
        games_30_plus_last_10=sum(1 for minute in minutes if minute >= 30.0),
        games_under_20_last_10=sum(1 for minute in minutes if minute < 20.0),
        minute_volatility=_minute_volatility(recent_rows),
    )


def _empty_report(player: Player, season: str) -> PlayerTrendReport:
    team_abbreviation = player.team.abbreviation if player.team else None
    return PlayerTrendReport(
        player_id=player.id,
        player_name=player.full_name,
        team_abbreviation=team_abbreviation,
        season=season,
        status="limited",
        window_games=0,
        role_status="stable_rotation",
        recent_form=PlayerTrendForm(),
        season_baseline=PlayerTrendForm(),
        trust_signals=PlayerTrendSignals(),
        impact_snapshot=PlayerTrendImpactSnapshot(pbp_coverage_status="none"),
        recommended_games=[],
    )


def _limited_report(
    player: Player,
    season: str,
    team_abbreviation: Optional[str],
    window_games: int,
    impact_snapshot: PlayerTrendImpactSnapshot,
) -> PlayerTrendReport:
    return PlayerTrendReport(
        player_id=player.id,
        player_name=player.full_name,
        team_abbreviation=team_abbreviation,
        season=season,
        status="limited",
        window_games=window_games,
        role_status="stable_rotation",
        recent_form=PlayerTrendForm(),
        season_baseline=PlayerTrendForm(),
        trust_signals=PlayerTrendSignals(),
        impact_snapshot=impact_snapshot,
        recommended_games=[],
    )


def build_player_trend_report(db: Session, player: Player, season: str) -> PlayerTrendReport:
    season_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player.id,
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .order_by(SeasonStat.gp.desc())
        .all()
    )
    season_row = season_rows[0] if season_rows else None
    team_abbreviation = season_row.team_abbreviation if season_row else (player.team.abbreviation if player.team else None)

    game_logs = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id == player.id,
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
        )
        .order_by(PlayerGameLog.game_date.desc(), PlayerGameLog.game_id.desc())
        .all()
    )

    on_off_row = (
        db.query(PlayerOnOff)
        .filter(
            PlayerOnOff.player_id == player.id,
            PlayerOnOff.season == season,
            PlayerOnOff.is_playoff == False,  # noqa: E712
        )
        .first()
    )

    impact_snapshot = PlayerTrendImpactSnapshot(
        pbp_coverage_status=_coverage_status(on_off_row, season_row),
        on_off_net=on_off_row.on_off_net if on_off_row else None,
        on_minutes=on_off_row.on_minutes if on_off_row else None,
        bpm=season_row.bpm if season_row else None,
        per=season_row.per if season_row else None,
        pts_pg=season_row.pts_pg if season_row else None,
        ts_pct=season_row.ts_pct if season_row else None,
    )

    if not game_logs:
        empty = _empty_report(player, season)
        empty.team_abbreviation = team_abbreviation
        empty.impact_snapshot = impact_snapshot
        return empty

    recent_rows = game_logs[:WINDOW_SIZE]

    if len(game_logs) < MIN_READY_GAMES:
        return _limited_report(
            player=player,
            season=season,
            team_abbreviation=team_abbreviation,
            window_games=len(recent_rows),
            impact_snapshot=impact_snapshot,
        )

    recent_form = _build_form(recent_rows)
    season_form = _build_form(game_logs)

    starter_rows = (
        db.query(GamePlayerStat.game_id, GamePlayerStat.is_starter)
        .filter(
            GamePlayerStat.player_id == player.id,
            GamePlayerStat.season == season,
            GamePlayerStat.game_id.in_([row.game_id for row in recent_rows]),
        )
        .all()
    ) if recent_rows else []
    starter_map = {game_id: bool(is_starter) for game_id, is_starter in starter_rows}

    signals = _trust_signals(
        recent_rows=recent_rows,
        season_form=season_form,
        recent_form=recent_form,
        starter_map=starter_map,
    )

    report = PlayerTrendReport(
        player_id=player.id,
        player_name=player.full_name,
        team_abbreviation=team_abbreviation,
        season=season,
        status="ready",
        window_games=len(recent_rows),
        role_status=_role_status(signals),
        recent_form=recent_form,
        season_baseline=season_form,
        trust_signals=signals,
        impact_snapshot=impact_snapshot,
        recommended_games=_recommended_games(recent_rows, season_form, starter_map),
    )
    return report


def _recommended_games(
    recent_rows: Sequence[PlayerGameLog],
    season_form: PlayerTrendForm,
    starter_map: Dict[str, bool],
) -> List[PlayerTrendGame]:
    scored_games = []
    season_minutes = season_form.avg_minutes or 0.0
    season_points = season_form.avg_points or 0.0
    season_plus_minus = season_form.avg_plus_minus or 0.0

    recent_starts = sum(1 for row in recent_rows if starter_map.get(row.game_id, False))

    for index, row in enumerate(recent_rows):
        is_starter = starter_map.get(row.game_id, False)
        minutes_deviation = abs((row.min or 0.0) - season_minutes)
        points_deviation = abs((row.pts or 0.0) - season_points)
        plus_minus_deviation = abs((row.plus_minus or 0.0) - season_plus_minus)
        priority = (
            minutes_deviation,
            1 if is_starter and recent_starts < 5 else 0,
            points_deviation,
            plus_minus_deviation,
            float(len(recent_rows) - index),
        )
        scored_games.append((priority, _game_note(row, starter_map, recent_starts, season_form), row, is_starter))

    scored_games.sort(reverse=True, key=lambda item: item[0])
    return [
        PlayerTrendGame(
            game_id=row.game_id,
            game_date=row.game_date.isoformat() if row.game_date else None,
            matchup=row.matchup,
            result=row.wl,
            minutes=_round_stat(row.min),
            points=row.pts,
            plus_minus=row.plus_minus,
            is_starter=is_starter,
            trend_note=note,
        )
        for _, note, row, is_starter in scored_games[:5]
    ]


def _game_note(
    row: PlayerGameLog,
    starter_map: Dict[str, bool],
    recent_starts: int,
    season_form: PlayerTrendForm,
) -> str:
    minutes = row.min or 0.0
    points = float(row.pts or 0.0)
    plus_minus = float(row.plus_minus or 0.0)
    season_minutes = season_form.avg_minutes or 0.0
    season_points = season_form.avg_points or 0.0
    season_plus_minus = season_form.avg_plus_minus or 0.0
    is_starter = starter_map.get(row.game_id, False)

    if is_starter and recent_starts < 5:
        return "starter look after bench stretch"
    if minutes - season_minutes >= 6.0:
        return "heavy workload spike"
    if season_minutes - minutes >= 6.0 and abs(points - season_points) < 5.0:
        return "minutes dip despite normal scoring"
    if abs(points - season_points) >= 10.0:
        return "big scoring outlier"
    if abs(plus_minus - season_plus_minus) >= 10.0:
        return "strong plus-minus swing"
    return "recent role check"
