from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GameTeamStat, LineupStats, Player, Team, WarehouseGame
from services.intel_math import clamp, estimate_possessions, safe_round
from services.style_feature_service import build_team_style_profile


PRIOR_POSSESSIONS = 60.0
MIN_CONFIDENCE_POSSESSIONS = 25.0


def _team_lookup(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return team


def _team_baseline(db: Session, team_id: int, season: str) -> Dict[str, Optional[float]]:
    rows = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.team_id == team_id, GameTeamStat.season == season)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="No team game stats found for the selected season.")

    totals = {
        "pts": 0.0,
        "opp_pts": 0.0,
        "fga": 0.0,
        "fta": 0.0,
        "oreb": 0.0,
        "tov": 0.0,
        "possessions": 0.0,
        "games": 0.0,
    }
    for row, game in rows:
        opponent_row = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.game_id == row.game_id, GameTeamStat.team_id != team_id)
            .first()
        )
        possessions = estimate_possessions(row.fga, row.oreb, row.tov, row.fta)
        totals["pts"] += float(row.pts or 0.0)
        totals["opp_pts"] += float(opponent_row.pts or 0.0) if opponent_row else 0.0
        totals["fga"] += float(row.fga or 0.0)
        totals["fta"] += float(row.fta or 0.0)
        totals["oreb"] += float(row.oreb or 0.0)
        totals["tov"] += float(row.tov or 0.0)
        totals["possessions"] += float(possessions or 0.0)
        totals["games"] += 1.0

    pace = totals["possessions"] / totals["games"] if totals["games"] else None
    net_rating = None
    if totals["possessions"] > 0:
        net_rating = ((totals["pts"] - totals["opp_pts"]) / totals["possessions"]) * 100.0

    return {
        "pace": safe_round(pace, 1),
        "net_rating": safe_round(net_rating, 2),
        "games": int(totals["games"]),
        "avg_points": safe_round(totals["pts"] / totals["games"], 1) if totals["games"] else None,
    }


def _resolve_player_names(db: Session, lineup_key: str) -> List[str]:
    player_ids = []
    for token in lineup_key.split("-"):
        token = token.strip()
        if not token:
            continue
        try:
            player_ids.append(int(token))
        except ValueError:
            continue
    if not player_ids:
        return []
    rows = db.query(Player).filter(Player.id.in_(player_ids)).all()
    name_map = {row.id: row.full_name for row in rows}
    return [name_map.get(pid, str(pid)) for pid in player_ids]


def _lineup_sample_confidence(possessions: Optional[int], minutes: Optional[float]) -> float:
    pos_term = clamp((float(possessions or 0.0) - MIN_CONFIDENCE_POSSESSIONS) / 80.0, 0.0, 1.0)
    minute_term = clamp(float(minutes or 0.0) / 80.0, 0.0, 1.0)
    return round(0.35 + (0.4 * pos_term) + (0.25 * minute_term), 2)


def _lineup_row(
    db: Session,
    lineup: LineupStats,
    baseline_net: float,
    team_pace: Optional[float],
    team_style: Optional[Dict[str, Any]],
    opponent_style: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    player_names = _resolve_player_names(db, lineup.lineup_key)
    observed_net = float(lineup.net_rating or 0.0)
    possessions = int(lineup.possessions or 0)
    minutes = float(lineup.minutes or 0.0)
    sample_weight = 0.0
    if possessions > 0:
        sample_weight = possessions / (possessions + PRIOR_POSSESSIONS)
    shrunk_net = (sample_weight * observed_net) + ((1.0 - sample_weight) * baseline_net)
    delta_net = shrunk_net - baseline_net
    possessions_per_game = float(team_pace or 0.0)
    expected_points_added_per_game = (delta_net / 100.0) * possessions_per_game
    if team_style and opponent_style and team_style.get("current_profile") and opponent_style.get("current_profile"):
        our_three = float(team_style["current_profile"].get("three_point_rate") or 0.0)
        opponent_three = float(opponent_style["current_profile"].get("three_point_rate") or 0.0)
        style_match_bonus = (our_three - opponent_three) * 2.0
    else:
        style_match_bonus = 0.0

    recommended_minutes_delta = clamp((delta_net / 2.5) + style_match_bonus, -6.0, 6.0)
    note = "Observed lineups are stronger than baseline." if delta_net > 0 else "Observed lineups are weaker than baseline."
    if possessions < MIN_CONFIDENCE_POSSESSIONS:
        note += " Sample is tiny, so the recommendation is directional only."

    return {
        "lineup_key": lineup.lineup_key,
        "player_names": player_names,
        "team_id": lineup.team_id,
        "season": lineup.season,
        "minutes": safe_round(minutes, 1),
        "possessions": possessions,
        "observed_net_rating": safe_round(observed_net, 2),
        "shrunk_net_rating": safe_round(shrunk_net, 2),
        "baseline_net_rating": safe_round(baseline_net, 2),
        "delta_net_rating": safe_round(delta_net, 2),
        "expected_points_added_per_game": safe_round(expected_points_added_per_game, 2),
        "expected_points_added_per_100": safe_round(delta_net, 2),
        "recommended_minutes_delta": safe_round(recommended_minutes_delta, 1),
        "confidence": _lineup_sample_confidence(possessions, minutes),
        "note": note,
    }


def build_lineup_impact_report(
    db: Session,
    team_abbr: str,
    season: str,
    opponent_abbr: Optional[str] = None,
    window_games: int = 10,
    min_possessions: int = 25,
) -> Dict[str, Any]:
    team = _team_lookup(db, team_abbr)
    baseline = _team_baseline(db, team.id, season)

    style_context = None
    opponent_context = None
    try:
        style_context = build_team_style_profile(db, team.abbreviation, season, window_games=window_games)
    except Exception:
        style_context = None
    if opponent_abbr:
        try:
            opponent_context = build_team_style_profile(db, opponent_abbr, season, window_games=window_games)
        except Exception:
            opponent_context = None

    lineups = (
        db.query(LineupStats)
        .filter(
            LineupStats.season == season,
            LineupStats.team_id == team.id,
            LineupStats.minutes.isnot(None),
            LineupStats.possessions.isnot(None),
            LineupStats.possessions >= min_possessions,
        )
        .all()
    )
    if not lineups:
        return {
            "team_abbreviation": team.abbreviation,
            "season": season,
            "filters": {
                "opponent_abbreviation": opponent_abbr.upper() if opponent_abbr else None,
                "window_games": window_games,
                "min_possessions": min_possessions,
            },
            "current_rotation": [],
            "recommended_rotation": [],
            "lineup_rows": [],
            "impact_summary": {
                "baseline_net_rating": baseline["net_rating"],
                "projected_net_rating": baseline["net_rating"],
                "expected_points_added_per_game": 0.0,
                "expected_points_added_per_100": 0.0,
            },
            "confidence": "low",
            "warnings": ["No qualifying lineups matched the current filters."],
        }

    lineup_rows = [
        _lineup_row(db, lineup, float(baseline["net_rating"] or 0.0), float(baseline["pace"] or 0.0), style_context, opponent_context)
        for lineup in lineups
    ]
    lineup_rows.sort(
        key=lambda row: (
            row["shrunk_net_rating"] if row["shrunk_net_rating"] is not None else -9999,
            row["possessions"],
        ),
        reverse=True,
    )

    current_rotation = sorted(
        lineup_rows,
        key=lambda row: row["minutes"] if row["minutes"] is not None else 0.0,
        reverse=True,
    )[:5]

    recommended_rotation = [
        dict(row, recommended_minutes_delta=safe_round(clamp(float(row["recommended_minutes_delta"] or 0.0), -6.0, 6.0), 1))
        for row in lineup_rows[:5]
    ]

    top_positive = [row for row in lineup_rows if (row["delta_net_rating"] or 0.0) > 0]
    projected_net = float(baseline["net_rating"] or 0.0)
    if top_positive:
        projected_net += sum(float(row["delta_net_rating"] or 0.0) for row in top_positive[:3]) / float(len(top_positive[:3]))

    expected_points_added_per_game = 0.0
    if current_rotation:
        expected_points_added_per_game = sum(
            float(row["expected_points_added_per_game"] or 0.0) for row in recommended_rotation
        ) / float(len(recommended_rotation) or 1)

    overall_confidence = "high" if all(float(row["confidence"] or 0.0) >= 0.65 for row in lineup_rows[:3]) else "moderate"
    warnings: List[str] = []
    if any(float(row["confidence"] or 0.0) < 0.5 for row in lineup_rows[:5]):
        warnings.append("Some recommended lineups are sample-limited and should be treated directionally.")
    if opponent_context is None and opponent_abbr:
        warnings.append("Opponent style context was unavailable, so opponent adjustments are muted.")

    return {
        "team_abbreviation": team.abbreviation,
        "season": season,
        "filters": {
            "opponent_abbreviation": opponent_abbr.upper() if opponent_abbr else None,
            "window_games": window_games,
            "min_possessions": min_possessions,
        },
        "current_rotation": current_rotation,
        "recommended_rotation": recommended_rotation,
        "lineup_rows": lineup_rows,
        "impact_summary": {
            "baseline_net_rating": baseline["net_rating"],
            "projected_net_rating": safe_round(projected_net, 2),
            "expected_points_added_per_game": safe_round(expected_points_added_per_game, 2),
            "expected_points_added_per_100": safe_round(projected_net - float(baseline["net_rating"] or 0.0), 2),
        },
        "confidence": overall_confidence,
        "warnings": warnings,
        "style_context": style_context,
        "opponent_context": opponent_context,
    }
