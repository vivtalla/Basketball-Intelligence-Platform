from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GamePlayerStat, GameTeamStat, PlayByPlayEvent, Team, WarehouseGame, LineupStats, Player
from services.intel_math import clamp, estimate_possessions, efg_pct, ftr, safe_round, three_point_rate, turnover_rate


def _team_lookup(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return team


def _week_key(game_date: Optional[date]) -> str:
    if not game_date:
        return "unknown"
    iso = game_date.isocalendar()
    return "{0}-W{1:02d}".format(iso[0], iso[1])


def _team_games(db: Session, team_id: int, season: str) -> List[Tuple[GameTeamStat, WarehouseGame]]:
    return (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.team_id == team_id, GameTeamStat.season == season)
        .order_by(WarehouseGame.game_date.asc().nullsfirst(), GameTeamStat.game_id.asc())
        .all()
    )


def _aggregate_team_game_profile(row: GameTeamStat, opponent_row: Optional[GameTeamStat]) -> Dict[str, Optional[float]]:
    possessions = estimate_possessions(row.fga, row.oreb, row.tov, row.fta)
    opp_oreb = float(opponent_row.oreb or 0.0) if opponent_row else None
    return {
        "pace": safe_round(possessions, 1),
        "three_point_rate": safe_round(three_point_rate(row.fg3a, row.fga), 3),
        "efg_pct": safe_round(efg_pct(row.fgm, row.fg3m, row.fga), 3),
        "ts_pct": safe_round(None if row.pts is None else (float(row.pts) / (2.0 * (float(row.fga or 0.0) + (0.44 * float(row.fta or 0.0))))), 3) if row.fga is not None else None,
        "turnover_rate": safe_round(turnover_rate(row.tov, row.fga, row.fta), 3),
        "ftr": safe_round(ftr(row.fta, row.fga), 3),
        "oreb_rate": safe_round(None if opp_oreb is None else float(row.oreb or 0.0) / max(1.0, float(row.oreb or 0.0) + opp_oreb), 3),
        "points": float(row.pts or 0.0),
        "opp_points": float(opponent_row.pts or 0.0) if opponent_row else None,
        "game_id": row.game_id,
    }


def _split_bench_starters(db: Session, game_id: str, team_abbr: str) -> Dict[str, Optional[float]]:
    rows = (
        db.query(GamePlayerStat)
        .filter(GamePlayerStat.game_id == game_id, GamePlayerStat.team_abbreviation == team_abbr)
        .all()
    )
    starters = [row for row in rows if row.is_starter]
    bench = [row for row in rows if not row.is_starter]
    starter_minutes = sum(float(row.min or 0.0) for row in starters)
    bench_minutes = sum(float(row.min or 0.0) for row in bench)
    starter_points = sum(float(row.pts or 0.0) for row in starters)
    bench_points = sum(float(row.pts or 0.0) for row in bench)
    starter_plus_minus = sum(float(row.plus_minus or 0.0) for row in starters)
    bench_plus_minus = sum(float(row.plus_minus or 0.0) for row in bench)
    return {
        "starter_minutes": starter_minutes,
        "bench_minutes": bench_minutes,
        "starter_points": starter_points,
        "bench_points": bench_points,
        "starter_plus_minus": starter_plus_minus,
        "bench_plus_minus": bench_plus_minus,
        "starter_count": len(starters),
        "bench_count": len(bench),
    }


def _late_game_proxy(db: Session, game_id: str, team_id: int) -> Dict[str, float]:
    rows = (
        db.query(PlayByPlayEvent)
        .filter(PlayByPlayEvent.game_id == game_id)
        .order_by(PlayByPlayEvent.order_index.asc())
        .all()
    )
    shot_events = 0
    turnover_events = 0
    ft_events = 0
    close_events = 0
    for row in rows:
        if row.team_id != team_id:
            continue
        if row.period is None or row.period < 4:
            continue
        close_events += 1
        if row.action_type in {"2pt", "3pt"}:
            shot_events += 1
        if row.action_type == "turnover":
            turnover_events += 1
        if row.action_type == "freethrow":
            ft_events += 1
    total = max(1, close_events)
    return {
        "shot_rate": shot_events / float(total),
        "turnover_rate": turnover_events / float(total),
        "ft_rate": ft_events / float(total),
        "close_events": float(close_events),
    }


def _build_series(rows: List[Dict[str, Optional[float]]], feature: str) -> List[Dict[str, Any]]:
    series: List[Dict[str, Any]] = []
    for row in rows:
        value = row.get(feature)
        if value is None:
            continue
        series.append({"label": row["week"], "value": safe_round(value, 3)})
    return series


def _trend_summary(label: str, recent_value: Optional[float], prior_value: Optional[float], positive_is_good: bool = True) -> Tuple[str, str, float]:
    if recent_value is None or prior_value is None:
        return ("flat", "insufficient data", 0.0)
    delta = float(recent_value) - float(prior_value)
    if not positive_is_good:
        delta = -delta
    direction = "up" if delta > 0.02 else "down" if delta < -0.02 else "flat"
    if direction == "up":
        summary = "{0} is moving in the right direction.".format(label)
    elif direction == "down":
        summary = "{0} is moving the wrong way.".format(label)
    else:
        summary = "{0} is mostly stable.".format(label)
    return direction, summary, abs(delta)


def _rotation_similarity(starters_by_game: List[set]) -> Optional[float]:
    if len(starters_by_game) < 2:
        return None
    similarities: List[float] = []
    for previous, current in zip(starters_by_game[:-1], starters_by_game[1:]):
        if not previous and not current:
            continue
        similarities.append(len(previous.intersection(current)) / float(len(previous.union(current)) or 1))
    if not similarities:
        return None
    return sum(similarities) / float(len(similarities))


def build_trend_card_report(
    db: Session,
    team_abbr: str,
    season: str,
    window_weeks: int = 4,
) -> Dict[str, Any]:
    team = _team_lookup(db, team_abbr)
    games = _team_games(db, team.id, season)
    if not games:
        return {
            "team_abbreviation": team.abbreviation,
            "season": season,
            "window_weeks": window_weeks,
            "cards": [],
            "warnings": ["No team games were found for the selected season."],
        }

    weekly: Dict[str, List[Dict[str, Optional[float]]]] = defaultdict(list)
    starters_by_game: List[set] = []
    for team_row, game in games:
        opponent_row = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.game_id == team_row.game_id, GameTeamStat.team_id != team.id)
            .first()
        )
        profile = _aggregate_team_game_profile(team_row, opponent_row)
        profile["week"] = _week_key(game.game_date)
        weekly[profile["week"]].append(profile)
        starters = {
            row.player_id
            for row in db.query(GamePlayerStat)
            .filter(
                GamePlayerStat.game_id == team_row.game_id,
                GamePlayerStat.team_abbreviation == team.abbreviation,
                GamePlayerStat.is_starter == True,  # noqa: E712
            )
            .all()
            if row.player_id is not None
        }
        starters_by_game.append(starters)

    ordered_weeks = sorted(weekly.keys())
    recent_weeks = ordered_weeks[-window_weeks:]
    prior_weeks = ordered_weeks[-(window_weeks * 2):-window_weeks] if len(ordered_weeks) > window_weeks else []

    def _avg_week(feature: str, weeks: List[str]) -> Optional[float]:
        values: List[float] = []
        for week in weeks:
            for row in weekly.get(week, []):
                if row.get(feature) is not None:
                    values.append(float(row[feature]))
        if not values:
            return None
        return sum(values) / float(len(values))

    recent_shot = _avg_week("three_point_rate", recent_weeks)
    prior_shot = _avg_week("three_point_rate", prior_weeks)
    recent_ts = _avg_week("ts_pct", recent_weeks)
    prior_ts = _avg_week("ts_pct", prior_weeks)
    recent_turnover = _avg_week("turnover_rate", recent_weeks)
    prior_turnover = _avg_week("turnover_rate", prior_weeks)
    recent_ftr = _avg_week("ftr", recent_weeks)
    prior_ftr = _avg_week("ftr", prior_weeks)

    shots_direction, shots_summary, shots_magnitude = _trend_summary("Shot profile", recent_shot, prior_shot)
    turnover_direction, turnover_summary, turnover_magnitude = _trend_summary("Turnover pressure", recent_turnover, prior_turnover, positive_is_good=False)
    foul_direction, foul_summary, foul_magnitude = _trend_summary("Foul pressure", recent_ftr, prior_ftr)
    ts_direction, ts_summary, ts_magnitude = _trend_summary("Efficiency", recent_ts, prior_ts)

    bench_recent = []
    bench_prior = []
    starter_recent = []
    starter_prior = []
    recent_game_ids = [game.game_id for _, game in games[-max(1, window_weeks):]]
    prior_game_ids = [game.game_id for _, game in games[-max(1, window_weeks * 2):-max(1, window_weeks)]]
    for game_id in recent_game_ids:
        split = _split_bench_starters(db, game_id, team.abbreviation)
        bench_recent.append(split["bench_points"] - split["starter_points"])
        starter_recent.append(split["starter_plus_minus"] - split["bench_plus_minus"])
    for game_id in prior_game_ids:
        split = _split_bench_starters(db, game_id, team.abbreviation)
        bench_prior.append(split["bench_points"] - split["starter_points"])
        starter_prior.append(split["starter_plus_minus"] - split["bench_plus_minus"])

    bench_recent_avg = sum(bench_recent) / float(len(bench_recent)) if bench_recent else None
    bench_prior_avg = sum(bench_prior) / float(len(bench_prior)) if bench_prior else None
    rotation_similarity = _rotation_similarity(starters_by_game[-max(1, window_weeks):])
    lineup_rows = (
        db.query(LineupStats)
        .filter(LineupStats.team_id == team.id, LineupStats.season == season, LineupStats.minutes.isnot(None))
        .order_by(LineupStats.net_rating.desc().nullslast(), LineupStats.minutes.desc())
        .limit(5)
        .all()
    )
    player_names = {}
    if lineup_rows:
        player_ids: List[int] = []
        for row in lineup_rows:
            for token in row.lineup_key.split("-"):
                try:
                    pid = int(token)
                    if pid not in player_ids:
                        player_ids.append(pid)
                except ValueError:
                    continue
        if player_ids:
            players = db.query(Player).filter(Player.id.in_(player_ids)).all()
            player_names = {player.id: player.full_name for player in players}

    cards: List[Dict[str, Any]] = [
        {
            "card_id": "shot-profile-drift",
            "scope": "team",
            "title": "Shot profile drift",
            "direction": shots_direction,
            "magnitude": safe_round(shots_magnitude, 3),
            "significance": "high" if shots_magnitude >= 0.05 else "medium" if shots_magnitude >= 0.02 else "low",
            "summary": shots_summary,
            "series": _build_series([{"week": week, "value": _avg_week("three_point_rate", [week])} for week in ordered_weeks], "value"),
            "supporting_stats": {
                "recent_three_point_rate": safe_round(recent_shot, 3),
                "prior_three_point_rate": safe_round(prior_shot, 3),
                "recent_ts_pct": safe_round(recent_ts, 3),
                "prior_ts_pct": safe_round(prior_ts, 3),
            },
            "drilldowns": [
                {"label": "Open team page", "url": "/teams/{0}".format(team.abbreviation)},
            ],
        },
        {
            "card_id": "turnover-pressure",
            "scope": "team",
            "title": "Turnover pressure",
            "direction": turnover_direction,
            "magnitude": safe_round(turnover_magnitude, 3),
            "significance": "high" if turnover_magnitude >= 0.03 else "medium" if turnover_magnitude >= 0.015 else "low",
            "summary": turnover_summary,
            "series": _build_series([{"week": week, "value": _avg_week("turnover_rate", [week])} for week in ordered_weeks], "value"),
            "supporting_stats": {
                "recent_turnover_rate": safe_round(recent_turnover, 3),
                "prior_turnover_rate": safe_round(prior_turnover, 3),
            },
            "drilldowns": [{"label": "Open rotation intelligence", "url": "/teams/{0}".format(team.abbreviation)}],
        },
        {
            "card_id": "bench-vs-starters",
            "scope": "team",
            "title": "Bench vs starters",
            "direction": "up" if bench_recent_avg is not None and bench_prior_avg is not None and bench_recent_avg > bench_prior_avg else "down",
            "magnitude": safe_round(abs((bench_recent_avg or 0.0) - (bench_prior_avg or 0.0)), 3),
            "significance": "high" if bench_recent_avg is not None and bench_prior_avg is not None and abs(bench_recent_avg - bench_prior_avg) >= 5 else "medium",
            "summary": "Bench production is {0} relative to the earlier window.".format("improving" if (bench_recent_avg or 0.0) > (bench_prior_avg or 0.0) else "slipping"),
            "series": [],
            "supporting_stats": {
                "recent_bench_minus_starters": safe_round(bench_recent_avg, 2),
                "prior_bench_minus_starters": safe_round(bench_prior_avg, 2),
            },
            "drilldowns": [{"label": "Open lineups", "url": "/teams/{0}?tab=lineups".format(team.abbreviation)}],
        },
        {
            "card_id": "rotation-drift",
            "scope": "team",
            "title": "Rotation drift",
            "direction": "up" if rotation_similarity is not None and rotation_similarity >= 0.6 else "down",
            "magnitude": safe_round(rotation_similarity, 3),
            "significance": "high" if rotation_similarity is not None and rotation_similarity < 0.45 else "medium",
            "summary": "The starter group is {0} stable over the recent window.".format("mostly" if rotation_similarity is not None and rotation_similarity >= 0.6 else "not very"),
            "series": [],
            "supporting_stats": {
                "recent_rotation_similarity": safe_round(rotation_similarity, 3),
                "recent_starter_sets": len(recent_game_ids),
            },
            "drilldowns": [{"label": "Open team rotation report", "url": "/teams/{0}".format(team.abbreviation)}],
        },
        {
            "card_id": "late-game-choices",
            "scope": "team",
            "title": "Late-game choices",
            "direction": ts_direction,
            "magnitude": safe_round(ts_magnitude, 3),
            "significance": "high" if ts_magnitude >= 0.03 else "medium" if ts_magnitude >= 0.015 else "low",
            "summary": ts_summary + " Late-game shot and turnover mix is the best lightweight clutch proxy we can see in Phase 1.",
            "series": [],
            "supporting_stats": {
                "recent_efficiency": safe_round(recent_ts, 3),
                "prior_efficiency": safe_round(prior_ts, 3),
                "recent_ftr": safe_round(recent_ftr, 3),
                "prior_ftr": safe_round(prior_ftr, 3),
            },
            "drilldowns": [{"label": "Open Game Explorer", "url": "/games"}],
        },
    ]

    if lineup_rows:
        best_lineup = lineup_rows[0]
        lineup_player_names = [player_names.get(int(token), token) for token in best_lineup.lineup_key.split("-") if token]
        cards.append(
            {
                "card_id": "core-lineup-stability",
                "scope": "lineup",
                "title": "Core lineup stability",
                "direction": "up" if (best_lineup.net_rating or 0.0) >= 0 else "down",
                "magnitude": safe_round(best_lineup.net_rating, 2),
                "significance": "high" if (best_lineup.minutes or 0.0) >= 60 else "medium",
                "summary": "{0} has the strongest season lineup signal and should stay on the staff radar.".format(" · ".join(lineup_player_names[:5]) if lineup_player_names else best_lineup.lineup_key),
                "series": [],
                "supporting_stats": {
                    "lineup_key": best_lineup.lineup_key,
                    "minutes": safe_round(best_lineup.minutes, 1),
                    "possessions": best_lineup.possessions,
                    "net_rating": safe_round(best_lineup.net_rating, 2),
                },
                "drilldowns": [{"label": "Open lineups", "url": "/teams/{0}?tab=lineups".format(team.abbreviation)}],
            }
        )

    warnings: List[str] = []
    if not cards:
        warnings.append("No trend cards could be generated for the current filters.")
    if len(recent_weeks) < window_weeks:
        warnings.append("Recent window is smaller than requested because the season has fewer weekly buckets.")

    return {
        "team_abbreviation": team.abbreviation,
        "season": season,
        "window_weeks": window_weeks,
        "cards": cards,
        "warnings": warnings,
    }
