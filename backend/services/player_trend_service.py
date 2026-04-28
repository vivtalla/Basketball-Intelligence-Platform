from __future__ import annotations

from statistics import pstdev
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from db.models import GamePlayerStat, Player, PlayerGameLog, PlayerOnOff, SeasonStat
from models.player import (
    PlayerTrendChangeEvidence,
    PlayerTrendForm,
    PlayerTrendGame,
    PlayerTrendImpactSnapshot,
    PlayerTrendReport,
    PlayerTrendSignals,
)
from services.analysis_context_service import contexts_for_window
from services.reliability_service import bayesian_change_score


WINDOW_SIZE = 10
MIN_READY_GAMES = 5
# Minimum baseline window (in games) needed for a usable change score; the
# Bayesian primitive wants ≥2 samples per side and ≥4 is where the variance
# estimate stops being trivially noisy.
MIN_BASELINE_GAMES = 4


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


def _role_status_reason(role_status: str, signals: PlayerTrendSignals) -> str:
    if role_status == "entrenched_starter":
        return "Starts are stable and recent minutes are holding near the season baseline."
    if role_status == "rising_rotation":
        return "Recent minutes or 30-plus-minute games are running above the season baseline."
    if role_status == "losing_trust":
        return "Recent minutes are down or too many recent games fell below 20 minutes."
    if role_status == "volatile_role":
        return "Recent minute volatility is high enough that the role read is noisy."
    return "Recent starts and minutes are close to the season baseline."


def _context_label(context_type: str, source: str) -> str:
    if context_type == "injury":
        return "Injury context" if source == "manual" else "Injury report context"
    if context_type == "recovery":
        return "Recovery window"
    if context_type == "availability_management":
        return "Availability management"
    return "Manual analyst note"


def _injury_context_summary(contexts) -> Optional[str]:
    relevant = [
        ctx for ctx in contexts
        if ctx.context_type in {"injury", "recovery", "availability_management"}
    ]
    if not relevant:
        return None
    primary = sorted(
        relevant,
        key=lambda ctx: (ctx.context_type != "injury", ctx.start_date is None, ctx.start_date),
    )[0]
    pieces = [_context_label(primary.context_type, primary.source)]
    if primary.start_date:
        if primary.end_date:
            pieces.append("{0} to {1}".format(primary.start_date.isoformat(), primary.end_date.isoformat()))
        else:
            pieces.append("since {0}".format(primary.start_date.isoformat()))
    if primary.note:
        pieces.append(primary.note)
    return " · ".join(pieces)


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


def _change_evidence(
    metric: str,
    recent_values: Sequence[Optional[float]],
    baseline_values: Sequence[Optional[float]],
) -> Optional[PlayerTrendChangeEvidence]:
    """Build a single change-evidence record from recent vs baseline samples.

    Returns None when the baseline is too thin to produce a stable variance
    estimate; the caller decides whether to skip the metric entirely or
    surface it without a probability.
    """
    recent_clean = [float(v) for v in recent_values if v is not None]
    baseline_clean = [float(v) for v in baseline_values if v is not None]
    if len(recent_clean) < 2 or len(baseline_clean) < MIN_BASELINE_GAMES:
        return None
    z_score, probability = bayesian_change_score(
        recent=recent_clean,
        baseline=baseline_clean,
        prior_variance=1.0,
    )
    if z_score is None or probability is None:
        return None
    direction = "above" if z_score > 0 else "below" if z_score < 0 else "level"
    if probability >= 0.70:
        interpretation = (
            "Recent window is meaningfully {0} the baseline — change probability {1:.0%}."
        ).format("above" if direction == "above" else "below", probability)
    elif probability <= 0.30:
        interpretation = (
            "Recent window matches the baseline within noise — change probability {0:.0%}."
        ).format(probability)
    else:
        interpretation = (
            "Recent window leans {0} the baseline but the evidence is mixed — change probability {1:.0%}."
        ).format("above" if direction == "above" else "below", probability)
    return PlayerTrendChangeEvidence(
        metric=metric,
        recent_mean=round(sum(recent_clean) / len(recent_clean), 2),
        baseline_mean=round(sum(baseline_clean) / len(baseline_clean), 2),
        z_score=z_score,
        posterior_change_probability=probability,
        interpretation=interpretation,
    )


def _build_change_evidence(
    recent_rows: Sequence[PlayerGameLog],
    baseline_rows: Sequence[PlayerGameLog],
) -> List[PlayerTrendChangeEvidence]:
    """Produce change-evidence rows for the metrics that drive the role-status
    label. We compute one entry per metric so readers can see which signal is
    actually moving — minutes vs scoring vs availability often disagree.
    """
    evidence: List[PlayerTrendChangeEvidence] = []
    candidates: List[Tuple[str, List[Optional[float]], List[Optional[float]]]] = [
        (
            "minutes",
            [row.min for row in recent_rows],
            [row.min for row in baseline_rows],
        ),
        (
            "points",
            [row.pts for row in recent_rows],
            [row.pts for row in baseline_rows],
        ),
        (
            "plus_minus",
            [row.plus_minus for row in recent_rows],
            [row.plus_minus for row in baseline_rows],
        ),
    ]
    for metric, recent_values, baseline_values in candidates:
        record = _change_evidence(metric, recent_values, baseline_values)
        if record is not None:
            evidence.append(record)
    return evidence


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
    role_status = _role_status(signals)
    recent_dates = [row.game_date for row in recent_rows if row.game_date is not None]
    context_rows = contexts_for_window(
        db=db,
        player_id=player.id,
        season=season,
        start_date=min(recent_dates) if recent_dates else None,
        end_date=max(recent_dates) if recent_dates else None,
        facet="trend",
    )
    injury_context = _injury_context_summary(context_rows)
    context_flags = []
    seen_flags = set()
    for ctx in context_rows:
        label = _context_label(ctx.context_type, ctx.source)
        if label not in seen_flags:
            context_flags.append(label)
            seen_flags.add(label)
    adjusted_role_status = None
    role_status_reason = _role_status_reason(role_status, signals)
    if role_status == "losing_trust" and injury_context:
        adjusted_role_status = "injury_context"
        role_status_reason = (
            "Recent minutes/production are down, but the recent window overlaps injury or recovery context; "
            "treat this as availability-affected rather than a clean trust-loss signal."
        )

    baseline_rows = game_logs[WINDOW_SIZE:]
    change_evidence = _build_change_evidence(recent_rows, baseline_rows)

    report = PlayerTrendReport(
        player_id=player.id,
        player_name=player.full_name,
        team_abbreviation=team_abbreviation,
        season=season,
        status="ready",
        window_games=len(recent_rows),
        role_status=role_status,
        recent_form=recent_form,
        season_baseline=season_form,
        trust_signals=signals,
        impact_snapshot=impact_snapshot,
        recommended_games=_recommended_games(recent_rows, season_form, starter_map),
        context_flags=context_flags,
        role_status_reason=role_status_reason,
        injury_context=injury_context,
        adjusted_role_status=adjusted_role_status,
        change_evidence=change_evidence,
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
