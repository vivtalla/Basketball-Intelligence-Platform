from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GameTeamStat, PlayByPlayEvent, Team, WarehouseGame
from services.intel_math import clamp, percentile_rank, safe_round


ACTION_FAMILIES = [
    "transition",
    "rim_pressure",
    "perimeter_creation",
    "post_mismatch",
    "handoff_pnr_proxy",
    "spot_up_proxy",
    "late_clock_bailout",
]


def _team_lookup(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return team


def _season_games(
    db: Session,
    team_id: int,
    season: str,
    opponent_abbr: Optional[str] = None,
    window_games: int = 10,
) -> List[Tuple[GameTeamStat, WarehouseGame]]:
    rows = (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.team_id == team_id, GameTeamStat.season == season)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )
    if opponent_abbr:
        opponent_upper = opponent_abbr.upper()
        filtered: List[Tuple[GameTeamStat, WarehouseGame]] = []
        for team_row, game in rows:
            opponent_row = (
                db.query(GameTeamStat)
                .filter(GameTeamStat.game_id == team_row.game_id, GameTeamStat.team_id != team_id)
                .first()
            )
            if opponent_row and opponent_row.team_abbreviation and opponent_row.team_abbreviation.upper() == opponent_upper:
                filtered.append((team_row, game))
        rows = filtered
    return rows[:window_games]


def _family_for_event(event: PlayByPlayEvent) -> Optional[str]:
    description = (event.description or "").lower()
    action_type = (event.action_type or "").lower()
    action_family = (event.action_family or "").lower()

    if "fast break" in description or "transition" in description or "run out" in description:
        return "transition"
    if "corner" in description or "catch and shoot" in description or "spot-up" in description or "spot up" in description:
        return "spot_up_proxy"
    if "handoff" in description or "dribble handoff" in description or "pick and roll" in description or "pnr" in description or "screen" in description:
        return "handoff_pnr_proxy"
    if "post" in description or "hook" in description or "mismatch" in description or "back to basket" in description:
        return "post_mismatch"
    if "iso" in description or "isolation" in description or "step back" in description or "pull-up" in description or "pull up" in description:
        return "perimeter_creation"
    if "late clock" in description or "buzzer" in description or "heave" in description or "end of quarter" in description:
        return "late_clock_bailout"
    if action_family == "shot":
        if action_type == "3pt":
            return "spot_up_proxy"
        if action_type == "2pt":
            if "paint" in description or "rim" in description or "layup" in description or "dunk" in description or "floater" in description:
                return "rim_pressure"
            return "perimeter_creation"
        if action_type == "freethrow":
            return "rim_pressure"
    if action_family == "turnover":
        return "perimeter_creation"
    return None


def _team_event_scores(
    db: Session,
    team_id: int,
    season: str,
    game_ids: Optional[Sequence[str]] = None,
) -> Dict[str, Dict[str, float]]:
    query = db.query(PlayByPlayEvent).filter(PlayByPlayEvent.season == season, PlayByPlayEvent.team_id == team_id)
    if game_ids:
        query = query.filter(PlayByPlayEvent.game_id.in_(list(game_ids)))
    rows = query.order_by(PlayByPlayEvent.game_id.asc(), PlayByPlayEvent.order_index.asc()).all()

    family_scores: Dict[str, Dict[str, float]] = defaultdict(lambda: {"usage": 0.0, "points": 0.0, "turnover_cost": 0.0, "foul_bonus": 0.0, "second_chance_bonus": 0.0, "events": 0.0})
    for row in rows:
        family = _family_for_event(row)
        if not family:
            continue
        entry = family_scores[family]
        entry["usage"] += 1.0
        entry["events"] += 1.0
        description = (row.description or "").lower()
        action_type = (row.action_type or "").lower()
        sub_type = (row.sub_type or "").lower()
        if action_type == "3pt" and sub_type == "made":
            entry["points"] += 3.0
        elif action_type == "2pt" and sub_type == "made":
            entry["points"] += 2.0
        elif action_type == "freethrow" and sub_type == "made":
            entry["points"] += 1.0
            entry["foul_bonus"] += 0.2
        elif action_type == "turnover":
            entry["turnover_cost"] += 1.0
            entry["points"] -= 1.0
        elif action_type == "rebound" and sub_type == "offensive":
            entry["second_chance_bonus"] += 0.4
            entry["points"] += 0.4
        elif "and-1" in description or "and one" in description:
            entry["foul_bonus"] += 0.3
        if "late clock" in description or "buzzer" in description or "heave" in description:
            entry["foul_bonus"] += 0.1
    return family_scores


def _normalize_family_rows(
    family_scores: Dict[str, Dict[str, float]],
    total_events: float,
    league_benchmark: Dict[str, Dict[str, float]],
    sample_games: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for family in ACTION_FAMILIES:
        entry = family_scores.get(family, {"usage": 0.0, "points": 0.0, "turnover_cost": 0.0, "foul_bonus": 0.0, "second_chance_bonus": 0.0, "events": 0.0})
        usage_rate = (entry["usage"] / total_events) if total_events else 0.0
        scoring_rate = (entry["points"] / entry["events"]) if entry["events"] else 0.0
        ev = scoring_rate + entry["foul_bonus"] + entry["second_chance_bonus"] - entry["turnover_cost"]
        benchmark = league_benchmark.get(family, {})
        league_ev = benchmark.get("ev")
        league_usage = benchmark.get("usage_rate")
        if league_ev is not None and league_usage is not None:
            ev_percentile = percentile_rank(ev, [float(item.get("ev", 0.0)) for item in league_benchmark.values() if item.get("ev") is not None])
            usage_percentile = percentile_rank(usage_rate, [float(item.get("usage_rate", 0.0)) for item in league_benchmark.values() if item.get("usage_rate") is not None])
        else:
            ev_percentile = None
            usage_percentile = None
        rows.append(
            {
                "action_family": family,
                "label": family.replace("_", " ").replace("proxy", "").strip().title(),
                "usage_rate": safe_round(usage_rate, 3),
                "raw_volume": int(entry["events"]),
                "ev": safe_round(ev, 3),
                "turnover_cost": safe_round(entry["turnover_cost"], 3),
                "foul_bonus": safe_round(entry["foul_bonus"], 3),
                "second_chance_bonus": safe_round(entry["second_chance_bonus"], 3),
                "league_percentile": safe_round(ev_percentile, 1) if ev_percentile is not None else None,
                "context_percentile": safe_round(usage_percentile, 1) if usage_percentile is not None else None,
                "sample_games": sample_games,
                "note": "Inferred from play-by-play descriptions and event families; not a native Synergy label.",
            }
        )
    return rows


def _league_benchmark(
    db: Session,
    season: str,
    team_id: Optional[int] = None,
) -> Dict[str, Dict[str, float]]:
    rows = db.query(PlayByPlayEvent).filter(PlayByPlayEvent.season == season)
    if team_id is not None:
        rows = rows.filter(PlayByPlayEvent.team_id == team_id)
    rows = rows.order_by(PlayByPlayEvent.game_id.asc(), PlayByPlayEvent.order_index.asc()).all()
    benchmark: Dict[str, Dict[str, float]] = {}
    per_family: Dict[str, List[float]] = defaultdict(list)
    per_usage: Dict[str, List[float]] = defaultdict(list)
    total_events = 0.0
    for row in rows:
        family = _family_for_event(row)
        if not family:
            continue
        total_events += 1.0
        points = 0.0
        action_type = (row.action_type or "").lower()
        sub_type = (row.sub_type or "").lower()
        if action_type == "3pt" and sub_type == "made":
            points = 3.0
        elif action_type == "2pt" and sub_type == "made":
            points = 2.0
        elif action_type == "freethrow" and sub_type == "made":
            points = 1.0
        elif action_type == "turnover":
            points = -1.0
        elif action_type == "rebound" and sub_type == "offensive":
            points = 0.4
        per_family[family].append(points)
        per_usage[family].append(1.0)
    for family in ACTION_FAMILIES:
        points_list = per_family.get(family, [])
        usage_list = per_usage.get(family, [])
        ev = (sum(points_list) / len(points_list)) if points_list else None
        usage_rate = (sum(usage_list) / total_events) if total_events else None
        benchmark[family] = {
            "ev": ev,
            "usage_rate": usage_rate,
        }
    return benchmark


def build_play_type_proxy_report(
    db: Session,
    team_abbr: str,
    season: str,
    opponent_abbr: Optional[str] = None,
    window_games: int = 10,
) -> Dict[str, Any]:
    team = _team_lookup(db, team_abbr)
    games = _season_games(db, team.id, season, opponent_abbr=opponent_abbr, window_games=window_games)
    if not games:
        return {
            "team_abbreviation": team.abbreviation,
            "season": season,
            "opponent_abbreviation": opponent_abbr.upper() if opponent_abbr else None,
            "window_games": window_games,
            "action_rows": [],
            "overused_flags": [],
            "underused_flags": [],
            "warnings": ["No games matched the current play-type window."],
        }

    game_ids = [game.game_id for _, game in games]
    family_scores = _team_event_scores(db, team.id, season, game_ids=game_ids)
    league_benchmark = _league_benchmark(db, season)
    rows = _normalize_family_rows(
        family_scores,
        sum(float(score["events"]) for score in family_scores.values()),
        league_benchmark,
        len(game_ids),
    )

    rows.sort(key=lambda item: item["ev"] if item["ev"] is not None else -999.0, reverse=True)

    overused_flags: List[Dict[str, Any]] = []
    underused_flags: List[Dict[str, Any]] = []
    league_evs = [float(item["ev"]) for item in rows if item.get("ev") is not None]
    league_usages = [float(item["usage_rate"]) for item in rows if item.get("usage_rate") is not None]
    avg_ev = sum(league_evs) / len(league_evs) if league_evs else 0.0
    avg_usage = sum(league_usages) / len(league_usages) if league_usages else 0.0

    for row in rows:
        ev = float(row["ev"] or 0.0)
        usage = float(row["usage_rate"] or 0.0)
        if usage >= avg_usage + 0.05 and ev <= avg_ev - 0.05:
            overused_flags.append(
                {
                    "action_family": row["action_family"],
                    "title": "{0} is overused for its return".format(row["label"]),
                    "summary": "This action family is taking a larger share than its current EV supports.",
                    "severity": "high" if usage >= avg_usage + 0.10 else "medium",
                    "confidence": "medium" if row["raw_volume"] < 30 else "high",
                    "evidence": [
                        {"label": "Usage rate", "value": row["usage_rate"]},
                        {"label": "EV", "value": row["ev"]},
                        {"label": "Raw volume", "value": row["raw_volume"]},
                    ],
                }
            )
        if usage <= avg_usage - 0.04 and ev >= avg_ev + 0.05:
            underused_flags.append(
                {
                    "action_family": row["action_family"],
                    "title": "{0} looks underused".format(row["label"]),
                    "summary": "This action family is generating better value than its current usage share suggests.",
                    "severity": "high" if ev >= avg_ev + 0.10 else "medium",
                    "confidence": "medium" if row["raw_volume"] < 30 else "high",
                    "evidence": [
                        {"label": "Usage rate", "value": row["usage_rate"]},
                        {"label": "EV", "value": row["ev"]},
                        {"label": "Raw volume", "value": row["raw_volume"]},
                    ],
                }
            )

    warnings: List[str] = []
    if not overused_flags:
        warnings.append("No over-used action families crossed the current threshold.")
    if not underused_flags:
        warnings.append("No under-used action families crossed the current threshold.")
    if len(game_ids) < window_games:
        warnings.append("Play-type proxy is using a smaller game window than requested.")

    return {
        "team_abbreviation": team.abbreviation,
        "season": season,
        "opponent_abbreviation": opponent_abbr.upper() if opponent_abbr else None,
        "window_games": len(game_ids),
        "action_rows": rows,
        "overused_flags": overused_flags,
        "underused_flags": underused_flags,
        "warnings": warnings,
    }
