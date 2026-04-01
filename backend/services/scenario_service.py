from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GameTeamStat, Team, WarehouseGame
from services.intel_math import clamp, estimate_possessions, efg_pct, ftr, safe_round, three_point_rate, turnover_rate
from services.style_feature_service import build_team_style_profile


FEATURE_KEYS = [
    "pace",
    "three_point_rate",
    "turnover_rate",
    "oreb_rate",
    "ftr",
    "ts_pct",
    "assist_rate",
]


def _team_lookup(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return team


def _game_profile(team_row: GameTeamStat, opponent_row: Optional[GameTeamStat]) -> Dict[str, Optional[float]]:
    possessions = estimate_possessions(team_row.fga, team_row.oreb, team_row.tov, team_row.fta)
    opp_dreb = float(opponent_row.dreb or 0.0) if opponent_row else None
    return {
        "pace": safe_round(possessions, 1),
        "three_point_rate": safe_round(three_point_rate(team_row.fg3a, team_row.fga), 3),
        "turnover_rate": safe_round(turnover_rate(team_row.tov, team_row.fga, team_row.fta), 3),
        "oreb_rate": safe_round(None if opp_dreb is None else float(team_row.oreb or 0.0) / max(1.0, float(team_row.oreb or 0.0) + opp_dreb), 3),
        "ftr": safe_round(ftr(team_row.fta, team_row.fga), 3),
        "ts_pct": safe_round(None if team_row.fga is None else (float(team_row.pts or 0.0) / (2.0 * (float(team_row.fga or 0.0) + (0.44 * float(team_row.fta or 0.0))))), 3),
        "assist_rate": safe_round(None if team_row.fgm in {None, 0} else float(team_row.ast or 0.0) / float(team_row.fgm), 3),
        "net_rating": safe_round(
            None if opponent_row is None or possessions is None else ((float(team_row.pts or 0.0) - float(opponent_row.pts or 0.0)) / possessions) * 100.0,
            2,
        ),
        "team_abbreviation": team_row.team_abbreviation,
        "game_id": team_row.game_id,
    }


def _coefficients(rows: List[Dict[str, Optional[float]]]) -> Dict[str, float]:
    coefficients: Dict[str, float] = {}
    target_values = [float(row["net_rating"]) for row in rows if row.get("net_rating") is not None]
    if not target_values:
        return {key: 0.0 for key in FEATURE_KEYS}

    target_mean = sum(target_values) / float(len(target_values))
    for feature in FEATURE_KEYS:
        feature_values = [float(row[feature]) for row in rows if row.get(feature) is not None and row.get("net_rating") is not None]
        paired_targets = [float(row["net_rating"]) for row in rows if row.get(feature) is not None and row.get("net_rating") is not None]
        if len(feature_values) < 3:
            coefficients[feature] = 0.0
            continue
        feature_mean = sum(feature_values) / float(len(feature_values))
        numerator = 0.0
        denominator = 0.0
        for value, target in zip(feature_values, paired_targets):
            numerator += (value - feature_mean) * (target - target_mean)
            denominator += (value - feature_mean) ** 2
        coefficients[feature] = numerator / denominator if denominator else 0.0
    return coefficients


def _scenario_adjustments(scenario_type: str, delta: float) -> Dict[str, float]:
    delta = abs(delta)
    if scenario_type == "reduce_iso_proxy":
        return {
            "turnover_rate": -0.6 * delta,
            "assist_rate": 0.4 * delta,
            "three_point_rate": 0.2 * delta,
        }
    if scenario_type == "increase_pnr_handoff_proxy":
        return {
            "assist_rate": 0.55 * delta,
            "ts_pct": 0.20 * delta,
            "three_point_rate": 0.15 * delta,
            "turnover_rate": -0.15 * delta,
        }
    if scenario_type == "raise_3pa_rate":
        return {
            "three_point_rate": 0.7 * delta,
            "pace": 0.1 * delta,
            "ts_pct": 0.10 * delta,
        }
    if scenario_type == "slow_pace":
        return {
            "pace": -0.7 * delta,
            "turnover_rate": -0.05 * delta,
            "ts_pct": -0.05 * delta,
        }
    if scenario_type == "increase_oreb_emphasis":
        return {
            "oreb_rate": 0.6 * delta,
            "ftr": 0.15 * delta,
            "turnover_rate": 0.05 * delta,
        }
    raise HTTPException(status_code=422, detail="Unsupported scenario_type '{0}'.".format(scenario_type))


def _scenario_label(scenario_type: str) -> str:
    return {
        "reduce_iso_proxy": "Reduce isolation-like possessions",
        "increase_pnr_handoff_proxy": "Increase P&R / handoff volume",
        "raise_3pa_rate": "Raise three-point rate",
        "slow_pace": "Slow the pace",
        "increase_oreb_emphasis": "Increase offensive rebounding emphasis",
    }.get(scenario_type, scenario_type)


def _closest_patterns(
    rows: List[Dict[str, Optional[float]]],
    target: Dict[str, float],
    limit: int = 3,
) -> List[Dict[str, Any]]:
    candidates: List[Tuple[float, Dict[str, Optional[float]]]] = []
    for row in rows:
        distance = 0.0
        support = 0
        for feature in FEATURE_KEYS:
            row_value = row.get(feature)
            target_value = target.get(feature)
            if row_value is None or target_value is None:
                continue
            distance += abs(float(row_value) - float(target_value))
            support += 1
        if support:
            candidates.append((distance / float(support), row))
    candidates.sort(key=lambda item: item[0])
    patterns: List[Dict[str, Any]] = []
    for distance, row in candidates[:limit]:
        patterns.append(
            {
                "team_abbreviation": row.get("team_abbreviation"),
                "game_id": row.get("game_id"),
                "season": row.get("season"),
                "distance": safe_round(distance, 3),
                "observed_net_rating": row.get("net_rating"),
                "summary": "This historical team-game window sat close to the requested scenario profile.",
            }
        )
    return patterns


def build_scenario_report(
    db: Session,
    team_abbr: str,
    season: str,
    scenario_type: str,
    delta: float,
    window_games: int = 10,
    opponent_abbr: Optional[str] = None,
) -> Dict[str, Any]:
    team = _team_lookup(db, team_abbr)
    style_profile = build_team_style_profile(db, team.abbreviation, season, window_games=window_games)
    current_profile = dict(style_profile["current_profile"])
    coefficients = _coefficients(
        [
            _game_profile(team_row, (
                db.query(GameTeamStat)
                .filter(GameTeamStat.game_id == team_row.game_id, GameTeamStat.team_id != team.id)
                .first()
            ))
            for team_row, game in (
                db.query(GameTeamStat, WarehouseGame)
                .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
                .all()
            )
        ]
    )

    adjustments = _scenario_adjustments(scenario_type, delta)
    target_profile: Dict[str, float] = {}
    for feature in FEATURE_KEYS:
        base_value = float(current_profile.get(feature) or 0.0)
        target_profile[feature] = base_value + float(adjustments.get(feature, 0.0))

    model_delta = 0.0
    driver_features: List[Dict[str, Any]] = []
    for feature, change in adjustments.items():
        coeff = coefficients.get(feature, 0.0)
        contribution = coeff * change
        model_delta += contribution
        driver_features.append(
            {
                "feature": feature,
                "change": safe_round(change, 3),
                "coefficient": safe_round(coeff, 3),
                "contribution": safe_round(contribution, 3),
            }
        )

    comparable_rows = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season)
        .all()
    )
    historical_profiles: List[Dict[str, Optional[float]]] = []
    for row, game in comparable_rows:
        opponent_row = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.game_id == row.game_id, GameTeamStat.team_id != row.team_id)
            .first()
        )
        profile = _game_profile(row, opponent_row)
        profile["season"] = row.season
        historical_profiles.append(profile)

    analog_patterns = _closest_patterns(historical_profiles, target_profile, limit=3)
    analog_delta = 0.0
    if analog_patterns:
        net_values = [float(item["observed_net_rating"]) for item in analog_patterns if item.get("observed_net_rating") is not None]
        if net_values:
            analog_delta = sum(net_values) / float(len(net_values)) - float(current_profile.get("net_rating") or 0.0)

    combined_delta = (0.7 * model_delta) + (0.3 * analog_delta)
    confidence_support = len([item for item in driver_features if abs(float(item["change"] or 0.0)) > 0])
    if confidence_support >= 4 and analog_patterns:
        confidence = "high"
    elif confidence_support >= 2 or analog_patterns:
        confidence = "medium"
    else:
        confidence = "low"

    if combined_delta > 0.5:
        direction = "up"
    elif combined_delta < -0.5:
        direction = "down"
    else:
        direction = "neutral"

    residual_band = max(1.0, abs(combined_delta) * 0.35)
    warnings: List[str] = []
    if confidence == "low":
        warnings.append("Scenario support is thin, so the result is directional only.")
    if opponent_abbr:
        warnings.append("Opponent-conditioned adjustments remain heuristic and should be read as contextual, not causal.")

    return {
        "team_abbreviation": team.abbreviation,
        "season": season,
        "scenario_type": scenario_type,
        "scenario_label": _scenario_label(scenario_type),
        "delta": delta,
        "window_games": window_games,
        "expected_direction": direction,
        "expected_net_rating_delta": safe_round(combined_delta, 2),
        "confidence": confidence,
        "range": {
            "low": safe_round(combined_delta - residual_band, 2),
            "high": safe_round(combined_delta + residual_band, 2),
        },
        "driver_features": driver_features,
        "comparable_patterns": analog_patterns,
        "warnings": warnings,
        "style_context": style_profile,
        "target_profile": target_profile,
        "model_summary": {
            "model_delta": safe_round(model_delta, 3),
            "analog_delta": safe_round(analog_delta, 3),
            "feature_support": confidence_support,
        },
    }
