from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import Team
from services.play_type_proxy_service import build_play_type_proxy_report
from services.style_feature_service import build_style_vector_lookup, build_team_style_profile
from services.intel_math import safe_round


ARCHETYPES: Dict[str, Dict[str, float]] = {
    "transition-leaning": {
        "pace": 75.0,
        "ts_pct": 58.0,
        "efg_pct": 57.0,
        "assist_rate": 55.0,
        "three_point_rate": 60.0,
        "paint_pressure": 45.0,
        "turnover_rate": 50.0,
        "oreb_rate": 40.0,
        "ftr": 45.0,
    },
    "three-point pressure": {
        "pace": 60.0,
        "ts_pct": 63.0,
        "efg_pct": 64.0,
        "assist_rate": 65.0,
        "three_point_rate": 85.0,
        "paint_pressure": 40.0,
        "turnover_rate": 45.0,
        "oreb_rate": 38.0,
        "ftr": 40.0,
    },
    "paint-driven": {
        "pace": 45.0,
        "ts_pct": 55.0,
        "efg_pct": 54.0,
        "assist_rate": 55.0,
        "three_point_rate": 35.0,
        "paint_pressure": 82.0,
        "turnover_rate": 48.0,
        "oreb_rate": 78.0,
        "ftr": 72.0,
    },
    "pick-and-roll / movement": {
        "pace": 58.0,
        "ts_pct": 61.0,
        "efg_pct": 61.0,
        "assist_rate": 82.0,
        "three_point_rate": 66.0,
        "paint_pressure": 52.0,
        "turnover_rate": 46.0,
        "oreb_rate": 42.0,
        "ftr": 48.0,
    },
    "iso-heavy": {
        "pace": 48.0,
        "ts_pct": 54.0,
        "efg_pct": 53.0,
        "assist_rate": 32.0,
        "three_point_rate": 52.0,
        "paint_pressure": 44.0,
        "turnover_rate": 60.0,
        "oreb_rate": 38.0,
        "ftr": 44.0,
    },
    "balanced": {
        "pace": 52.0,
        "ts_pct": 56.0,
        "efg_pct": 56.0,
        "assist_rate": 58.0,
        "three_point_rate": 52.0,
        "paint_pressure": 52.0,
        "turnover_rate": 50.0,
        "oreb_rate": 50.0,
        "ftr": 50.0,
    },
}


def _team_lookup(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return team


def _vector_from_profile(profile: Dict[str, Any]) -> Dict[str, float]:
    league_context = profile.get("league_context") or {}
    vector: Dict[str, float] = {}
    for feature in ARCHETYPES["balanced"].keys():
        percentile = None
        if isinstance(league_context.get(feature), dict):
            percentile = league_context[feature].get("percentile")
        vector[feature] = float(percentile if percentile is not None else 50.0)
    return vector


def _distance(vector: Dict[str, float], centroid: Dict[str, float]) -> float:
    total = 0.0
    count = 0
    for feature, centroid_value in centroid.items():
        if feature not in vector:
            continue
        total += abs(vector[feature] - centroid_value)
        count += 1
    return total / float(count or 1)


def _top_contributors(vector: Dict[str, float], centroid: Dict[str, float]) -> List[Dict[str, Any]]:
    deltas = []
    for feature, centroid_value in centroid.items():
        current_value = vector.get(feature)
        if current_value is None:
            continue
        deltas.append((feature, current_value - centroid_value))
    deltas.sort(key=lambda item: abs(item[1]), reverse=True)
    return [
        {
            "feature": feature,
            "delta": safe_round(delta, 1),
            "direction": "above" if delta > 0 else "below" if delta < 0 else "aligned",
        }
        for feature, delta in deltas[:3]
    ]


def _infer_label_from_play_type(primary_family: Optional[str], fallback_label: str) -> str:
    if not primary_family:
        return fallback_label
    if primary_family == "handoff_pnr_proxy":
        return "pick-and-roll / movement"
    if primary_family == "spot_up_proxy":
        return "three-point pressure"
    if primary_family == "transition":
        return "transition-leaning"
    if primary_family == "post_mismatch":
        return "paint-driven"
    if primary_family == "perimeter_creation":
        return "iso-heavy"
    return fallback_label


def build_style_xray_report(
    db: Session,
    team_abbr: str,
    season: str,
    window_games: int = 10,
) -> Dict[str, Any]:
    team = _team_lookup(db, team_abbr)
    profile = build_team_style_profile(db, team.abbreviation, season, window_games=window_games)
    vector = _vector_from_profile(profile)
    play_type_report = None
    try:
        play_type_report = build_play_type_proxy_report(db, team.abbreviation, season, window_games=window_games)
    except Exception:
        play_type_report = None

    archetype_scores: List[Tuple[str, float]] = []
    for archetype, centroid in ARCHETYPES.items():
        archetype_scores.append((archetype, _distance(vector, centroid)))
    archetype_scores.sort(key=lambda item: item[1])
    primary_label = archetype_scores[0][0]

    if play_type_report and play_type_report.get("action_rows"):
        top_family = play_type_report["action_rows"][0]["action_family"]
        primary_label = _infer_label_from_play_type(top_family, primary_label)

    primary_centroid = ARCHETYPES.get(primary_label, ARCHETYPES["balanced"])
    feature_contributors = _top_contributors(vector, primary_centroid)

    league_profiles = build_style_vector_lookup(db, season, window_games=window_games)
    neighbors: List[Dict[str, Any]] = []
    for other in league_profiles:
        if other["team_abbreviation"] == team.abbreviation:
            continue
        other_vector = _vector_from_profile(other)
        distance = _distance(vector, other_vector)
        neighbors.append(
            {
                "team_abbreviation": other["team_abbreviation"],
                "team_name": other["team_name"],
                "style_label": other["style_label"],
                "distance": safe_round(distance, 3),
                "recent_drift": other.get("recent_drift"),
            }
        )
    neighbors.sort(key=lambda item: item["distance"] if item["distance"] is not None else 999.0)

    adjacent_archetypes: List[Dict[str, Any]] = []
    for archetype, distance in archetype_scores[1:3]:
        adjacent_archetypes.append(
            {
                "label": archetype,
                "distance": safe_round(distance, 3),
                "summary": "Closest alternate identity to the current team shape.",
                "feature_contributors": _top_contributors(vector, ARCHETYPES[archetype]),
            }
        )

    top_two_distance = archetype_scores[1][1] if len(archetype_scores) > 1 else archetype_scores[0][1]
    stability = {
        "state": "stable" if (top_two_distance - archetype_scores[0][1]) >= 4.0 else "mixed",
        "distance_gap": safe_round((top_two_distance - archetype_scores[0][1]) if len(archetype_scores) > 1 else 0.0, 3),
        "label_margin": safe_round(abs(archetype_scores[0][1] - archetype_scores[1][1]) if len(archetype_scores) > 1 else 0.0, 3),
    }

    warnings: List[str] = []
    if not league_profiles:
        warnings.append("League archetype neighbors are thin, so the x-ray is using only the current team profile.")
    if play_type_report is None or not play_type_report.get("action_rows"):
        warnings.append("Play-type proxy data was unavailable, so the archetype label comes from style features only.")

    return {
        "team_abbreviation": team.abbreviation,
        "team_name": team.name,
        "season": season,
        "window_games": window_games,
        "archetype": primary_label,
        "style_label": profile["style_label"],
        "feature_contributors": feature_contributors,
        "nearest_neighbors": neighbors[:5],
        "adjacent_archetypes": adjacent_archetypes,
        "stability": stability,
        "play_type_mix": play_type_report,
        "recent_movement": profile.get("recent_drift"),
        "warnings": warnings,
    }

