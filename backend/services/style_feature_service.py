from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from db.models import GameTeamStat, Team, WarehouseGame
from services.intel_math import (
    clamp,
    efg_pct,
    estimate_possessions,
    ftr,
    mean,
    oreb_rate,
    percentile_rank,
    rate,
    safe_round,
    three_point_rate,
    turnover_rate,
)


STYLE_FEATURES = [
    "pace",
    "ts_pct",
    "efg_pct",
    "assist_rate",
    "three_point_rate",
    "paint_pressure",
    "transition_proxy",
    "turnover_rate",
    "oreb_rate",
    "ftr",
]


def _team_query(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise ValueError("Team '{0}' not found.".format(team_abbr))
    return team


def _game_rows(db: Session, team_id: int, season: str) -> List[Tuple[GameTeamStat, WarehouseGame]]:
    return (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.team_id == team_id, GameTeamStat.season == season)
        .order_by(WarehouseGame.game_date.asc().nullsfirst(), GameTeamStat.game_id.asc())
        .all()
    )


def _team_game_profile(row: GameTeamStat, opponent_row: Optional[GameTeamStat] = None) -> Dict[str, Optional[float]]:
    possessions = estimate_possessions(row.fga, row.oreb, row.tov, row.fta)
    opponent_dreb = float(opponent_row.dreb or 0.0) if opponent_row is not None else None
    opponent_oreb = float(opponent_row.oreb or 0.0) if opponent_row is not None else None
    return {
        "pace": safe_round(possessions, 1),
        "ts_pct": safe_round(
            None if possessions is None else (float(row.pts or 0.0) / (2.0 * (float(row.fga or 0.0) + (0.44 * float(row.fta or 0.0))))),
            3,
        ),
        "efg_pct": safe_round(efg_pct(row.fgm, row.fg3m, row.fga), 3),
        "assist_rate": safe_round(rate(row.ast, row.fgm), 3),
        "three_point_rate": safe_round(three_point_rate(row.fg3a, row.fga), 3),
        "paint_pressure": safe_round(
            clamp(1.0 - float(three_point_rate(row.fg3a, row.fga) or 0.0) + 0.2 * float(ftr(row.fta, row.fga) or 0.0), 0.0, 2.0),
            3,
        ),
        "transition_proxy": safe_round(
            clamp((float(possessions or 0.0) / 100.0) + 0.15 * float(three_point_rate(row.fg3a, row.fga) or 0.0), 0.0, 2.5),
            3,
        ),
        "turnover_rate": safe_round(turnover_rate(row.tov, row.fga, row.fta), 3),
        "oreb_rate": safe_round(oreb_rate(row.oreb, opponent_dreb), 3),
        "ftr": safe_round(ftr(row.fta, row.fga), 3),
        "rebounding_margin": safe_round(
            None if opponent_oreb is None else float(row.oreb or 0.0) - opponent_oreb,
            2,
        ),
        "points": safe_round(float(row.pts or 0.0), 1),
        "net_rating": safe_round(
            None if possessions is None else ((float(row.pts or 0.0) - float(opponent_row.pts or 0.0)) / possessions) * 100.0 if opponent_row is not None else None,
            2,
        ),
    }


def _aggregate_profiles(rows: Sequence[Dict[str, Optional[float]]]) -> Dict[str, Optional[float]]:
    profile = {key: None for key in STYLE_FEATURES}
    if not rows:
        return profile

    profile["pace"] = mean(row.get("pace") for row in rows)
    profile["ts_pct"] = mean(row.get("ts_pct") for row in rows)
    profile["efg_pct"] = mean(row.get("efg_pct") for row in rows)
    profile["assist_rate"] = mean(row.get("assist_rate") for row in rows)
    profile["three_point_rate"] = mean(row.get("three_point_rate") for row in rows)
    profile["paint_pressure"] = mean(row.get("paint_pressure") for row in rows)
    profile["transition_proxy"] = mean(row.get("transition_proxy") for row in rows)
    profile["turnover_rate"] = mean(row.get("turnover_rate") for row in rows)
    profile["oreb_rate"] = mean(row.get("oreb_rate") for row in rows)
    profile["ftr"] = mean(row.get("ftr") for row in rows)
    return profile


def _league_context(rows: Sequence[Dict[str, Optional[float]]]) -> Dict[str, Dict[str, Optional[float]]]:
    context: Dict[str, Dict[str, Optional[float]]] = {}
    for feature in STYLE_FEATURES:
        values = [float(row[feature]) for row in rows if row.get(feature) is not None]
        if not values:
            context[feature] = {"mean": None, "p25": None, "p50": None, "p75": None, "min": None, "max": None, "percentile": None}
            continue
        sorted_values = sorted(values)
        median_index = len(sorted_values) // 2
        context[feature] = {
            "mean": safe_round(sum(values) / float(len(values)), 3),
            "p25": safe_round(sorted_values[int(len(sorted_values) * 0.25)], 3),
            "p50": safe_round(sorted_values[median_index], 3),
            "p75": safe_round(sorted_values[int(len(sorted_values) * 0.75) if len(sorted_values) > 1 else -1], 3),
            "min": safe_round(sorted_values[0], 3),
            "max": safe_round(sorted_values[-1], 3),
            "percentile": None,
        }
    return context


def _style_label(profile: Dict[str, Optional[float]], league_rows: Sequence[Dict[str, Optional[float]]]) -> str:
    pace = profile.get("pace")
    three_point_rate_value = profile.get("three_point_rate")
    assist_rate_value = profile.get("assist_rate")
    paint_pressure = profile.get("paint_pressure")
    turnover = profile.get("turnover_rate")
    transition = profile.get("transition_proxy")

    pace_pct = percentile_rank(pace, [float(row["pace"]) for row in league_rows if row.get("pace") is not None]) if pace is not None else None
    three_pct = percentile_rank(three_point_rate_value, [float(row["three_point_rate"]) for row in league_rows if row.get("three_point_rate") is not None]) if three_point_rate_value is not None else None
    assist_pct = percentile_rank(assist_rate_value, [float(row["assist_rate"]) for row in league_rows if row.get("assist_rate") is not None]) if assist_rate_value is not None else None
    paint_pct = percentile_rank(paint_pressure, [float(row["paint_pressure"]) for row in league_rows if row.get("paint_pressure") is not None]) if paint_pressure is not None else None
    turnover_pct = percentile_rank(turnover, [float(row["turnover_rate"]) for row in league_rows if row.get("turnover_rate") is not None]) if turnover is not None else None
    transition_pct = percentile_rank(transition, [float(row["transition_proxy"]) for row in league_rows if row.get("transition_proxy") is not None]) if transition is not None else None

    if assist_pct is not None and assist_pct >= 70 and three_pct is not None and three_pct >= 60:
        return "pick-and-roll / movement"
    if pace_pct is not None and pace_pct >= 70 and transition_pct is not None and transition_pct >= 65:
        return "transition-leaning"
    if three_pct is not None and three_pct >= 70:
        return "three-point pressure"
    if paint_pct is not None and paint_pct >= 70 and three_pct is not None and three_pct <= 40:
        return "paint-driven"
    if turnover_pct is not None and turnover_pct >= 65:
        return "chaos-prone"
    if pace_pct is not None and pace_pct <= 35 and paint_pct is not None and paint_pct >= 55:
        return "halfcourt / pressure"
    return "balanced"


def _recent_drift(recent_profile: Dict[str, Optional[float]], season_profile: Dict[str, Optional[float]]) -> Dict[str, Optional[float]]:
    drift: Dict[str, Optional[float]] = {}
    for feature in STYLE_FEATURES:
        recent_value = recent_profile.get(feature)
        season_value = season_profile.get(feature)
        drift[feature] = None if recent_value is None or season_value is None else safe_round(recent_value - season_value, 3)
    return drift


def _scenario_bins(profile: Dict[str, Optional[float]], league_rows: Sequence[Dict[str, Optional[float]]]) -> List[Dict[str, Any]]:
    pace = profile.get("pace") or 0.0
    ts = profile.get("ts_pct") or 0.0
    three_point_rate_value = profile.get("three_point_rate") or 0.0
    turnover = profile.get("turnover_rate") or 0.0
    oreb = profile.get("oreb_rate") or 0.0

    league_pace = [float(row["pace"]) for row in league_rows if row.get("pace") is not None]
    league_net = [float(row["net_rating"]) for row in league_rows if row.get("net_rating") is not None]
    pace_reference = sum(league_pace) / len(league_pace) if league_pace else 0.0
    net_reference = sum(league_net) / len(league_net) if league_net else 0.0

    bins: List[Dict[str, Any]] = []
    for label, pace_delta, three_delta, turnover_delta, oreb_delta in [
        ("Play faster", 4.0, 0.0, 0.0, 0.0),
        ("Play slower", -4.0, 0.0, 0.0, 0.0),
        ("Raise three-point rate", 0.0, 0.05, 0.0, 0.0),
        ("Reduce turnovers", 0.0, 0.0, -0.03, 0.0),
        ("Crash the glass harder", 0.0, 0.0, 0.0, 0.04),
    ]:
        projected_pace = pace + pace_delta
        pace_signal = (projected_pace - pace_reference) * 0.35
        spacing_signal = three_delta * 18.0
        turnover_signal = turnover_delta * -22.0
        rebound_signal = oreb_delta * 16.0
        baseline_signal = (ts - 0.55) * 10.0
        projected_net = net_reference + pace_signal + spacing_signal + turnover_signal + rebound_signal + baseline_signal
        confidence = clamp(0.45 + min(0.3, abs(pace_delta) / 10.0) + min(0.15, abs(three_delta) * 2.0) + min(0.1, abs(turnover_delta) * 3.0), 0.35, 0.85)
        bins.append(
            {
                "label": label,
                "pace_delta": pace_delta,
                "three_point_rate_delta": three_delta,
                "turnover_rate_delta": turnover_delta,
                "oreb_rate_delta": oreb_delta,
                "projected_net_rating_delta": safe_round(projected_net - net_reference, 2),
                "confidence": safe_round(confidence, 2),
                "summary": "Historical context suggests this would likely move the team by roughly {0} net rating points.".format(
                    safe_round(projected_net - net_reference, 1)
                ),
            }
        )
    return bins


def build_team_style_profile(
    db: Session,
    team_abbr: str,
    season: str,
    window_games: int = 10,
) -> Dict[str, Any]:
    team = _team_query(db, team_abbr)
    rows = _game_rows(db, team.id, season)
    if not rows:
        raise ValueError("No team game stats found for {0} in {1}.".format(team_abbr.upper(), season))

    league_rows_raw = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season)
        .all()
    )

    team_rows: List[Dict[str, Optional[float]]] = []
    recent_rows: List[Dict[str, Optional[float]]] = []

    for index, (row, game) in enumerate(rows):
        opponent_row = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.game_id == row.game_id, GameTeamStat.team_id != team.id)
            .first()
        )
        profile = _team_game_profile(row, opponent_row)
        team_rows.append(profile)
        if index >= max(0, len(rows) - window_games):
            recent_rows.append(profile)

    season_profile = _aggregate_profiles(team_rows)
    recent_profile = _aggregate_profiles(recent_rows)
    drift = _recent_drift(recent_profile, season_profile)
    league_rows: List[Dict[str, Optional[float]]] = []
    for league_row, league_game in league_rows_raw:
        opponent_row = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.game_id == league_row.game_id, GameTeamStat.team_id != league_row.team_id)
            .first()
        )
        league_rows.append(_team_game_profile(league_row, opponent_row))

    league_context = _league_context(league_rows)

    for feature in STYLE_FEATURES:
        league_context[feature]["percentile"] = percentile_rank(
            season_profile.get(feature),
            [float(row[feature]) for row in league_rows if row.get(feature) is not None],
        )

    pace_values = [float(row["pace"]) for row in league_rows if row.get("pace") is not None]
    league_label = _style_label(season_profile, team_rows)
    return {
        "team_abbreviation": team.abbreviation,
        "team_name": team.name,
        "season": season,
        "window_games": min(window_games, len(rows)),
        "style_label": league_label,
        "current_profile": season_profile,
        "recent_profile": recent_profile,
        "recent_drift": drift,
        "league_context": league_context,
        "scenario_bins": _scenario_bins(season_profile, team_rows),
        "warnings": ["Recent window is smaller than the requested size."] if len(recent_rows) < window_games else [],
        "supporting_games": len(rows),
        "pace_percentile": percentile_rank(season_profile.get("pace"), pace_values),
    }


def build_style_vector_lookup(
    db: Session,
    season: str,
    window_games: int = 10,
) -> List[Dict[str, Any]]:
    teams = db.query(Team).order_by(Team.abbreviation.asc()).all()
    vectors: List[Dict[str, Any]] = []
    for team in teams:
        try:
            profile = build_team_style_profile(db, team.abbreviation, season, window_games=window_games)
        except Exception:
            continue
        vectors.append(profile)
    return vectors
