from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.cache import CacheManager
from db.database import get_db
from db.models import GameTeamStat, PlayByPlayEvent, Team, WarehouseGame
from models.styles import (
    ComparisonMetricRow,
    ComparisonStory,
    LineupComparisonEntity,
    LineupComparisonResponse,
    StyleComparisonEntity,
    StyleComparisonResponse,
    StyleFeatureContributor,
    StyleLaunchLinks,
    StyleMetricRow,
    StyleNeighbor,
    StyleScenarioLink,
    StyleScenarioBin,
    StyleXRayResponse,
    TeamStyleProfileResponse,
)

router = APIRouter()


_STYLE_METRICS: List[Tuple[str, str, bool, str]] = [
    ("off_rating", "Offensive Rating", True, "number"),
    ("def_rating", "Defensive Rating", False, "number"),
    ("net_rating", "Net Rating", True, "signed"),
    ("pace", "Pace", True, "number"),
    ("ts_pct", "True Shooting%", True, "percent"),
    ("efg_pct", "Effective FG%", True, "percent"),
    ("three_point_rate", "3PA Rate", True, "percent"),
    ("ftr", "Free Throw Rate", True, "percent"),
    ("oreb_rate", "Offensive Rebound Rate", True, "percent"),
    ("turnover_rate", "Turnover Rate", False, "percent"),
    ("assist_rate", "Assist Rate", True, "percent"),
    ("transition_rate", "Transition Rate", True, "percent"),
    ("paint_pressure_proxy", "Paint Pressure Proxy", True, "number"),
]


def _safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _safe_div(numerator: float, denominator: float) -> Optional[float]:
    if denominator <= 0:
        return None
    return numerator / denominator


def _estimate_possessions(row: GameTeamStat) -> Optional[float]:
    possessions = float(row.fga or 0) - float(row.oreb or 0) + float(row.tov or 0) + (0.44 * float(row.fta or 0))
    if possessions <= 0:
        return None
    return possessions


def _fetch_team(db: Session, abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr))
    return team


def _style_cache_key(prefix: str, parts: List[str]) -> str:
    return "{0}:{1}".format(prefix, ":".join(parts))


def _season_watermark(db: Session, season: str) -> str:
    max_team = db.query(func.max(GameTeamStat.updated_at)).filter(GameTeamStat.season == season).scalar()
    max_pbp = db.query(func.max(PlayByPlayEvent.updated_at)).filter(PlayByPlayEvent.season == season).scalar()
    watermark = max([value for value in [max_team, max_pbp] if value is not None], default=None)
    return watermark.isoformat() if watermark else "none"


def _transition_rate(db: Session, game_ids: List[str], team_id: int) -> Optional[float]:
    if not game_ids:
        return None
    events = (
        db.query(PlayByPlayEvent)
        .filter(PlayByPlayEvent.game_id.in_(game_ids), PlayByPlayEvent.team_id == team_id)
        .order_by(PlayByPlayEvent.game_id.asc(), PlayByPlayEvent.order_index.asc())
        .all()
    )
    shot_events = 0
    transition_events = 0
    for event in events:
        desc = (event.description or "").lower()
        if event.action_type in {"2pt", "3pt", "freethrow"}:
            shot_events += 1
            if any(token in desc for token in ["fast break", "transition", "runout", "leak out", "leak-out"]):
                transition_events += 1
    if shot_events == 0:
        return None
    return transition_events / float(shot_events)


def _build_team_vector(
    db: Session,
    team: Team,
    rows: List[GameTeamStat],
    opponent_rows: Dict[str, GameTeamStat],
    transition_rate: Optional[float],
) -> Dict[str, Optional[float]]:
    games = float(len(rows))
    total_pts = sum(float(row.pts or 0) for row in rows)
    total_fga = sum(float(row.fga or 0) for row in rows)
    total_fgm = sum(float(row.fgm or 0) for row in rows)
    total_fg3m = sum(float(row.fg3m or 0) for row in rows)
    total_fg3a = sum(float(row.fg3a or 0) for row in rows)
    total_fta = sum(float(row.fta or 0) for row in rows)
    total_oreb = sum(float(row.oreb or 0) for row in rows)
    total_dreb = sum(float(row.dreb or 0) for row in rows)
    total_tov = sum(float(row.tov or 0) for row in rows)
    total_ast = sum(float(row.ast or 0) for row in rows)
    team_minutes = sum(float(row.minutes or 0) for row in rows)
    possessions = sum((_estimate_possessions(row) or 0.0) for row in rows)
    opponent_points = sum(float(opponent_rows[row.game_id].pts or 0) for row in rows if row.game_id in opponent_rows)

    pace = None
    if team_minutes > 0 and possessions > 0:
        pace = possessions * 48.0 / team_minutes
    elif games > 0 and possessions > 0:
        pace = possessions / games

    off_rating = _safe_div(total_pts * 100.0, possessions)
    def_rating = _safe_div(opponent_points * 100.0, possessions)
    net_rating = None
    if off_rating is not None and def_rating is not None:
        net_rating = off_rating - def_rating

    ts_denominator = 2.0 * (total_fga + (0.44 * total_fta))
    ts_pct = _safe_div(total_pts, ts_denominator)
    efg_pct = _safe_div(total_fgm + (0.5 * total_fg3m), total_fga)
    three_point_rate = _safe_div(total_fg3a, total_fga)
    ftr = _safe_div(total_fta, total_fga)
    oreb_rate = _safe_div(total_oreb, total_oreb + total_dreb)
    turnover_rate = _safe_div(total_tov, possessions)
    assist_rate = _safe_div(total_ast, total_fgm)
    paint_pressure_proxy = None
    if ftr is not None and oreb_rate is not None and three_point_rate is not None:
        paint_pressure_proxy = (ftr * 0.55) + (oreb_rate * 0.25) + ((1.0 - three_point_rate) * 0.20)

    if transition_rate is None and total_fga > 0:
        transition_rate = 0.0

    return {
        "games": games,
        "pts": total_pts,
        "off_rating": off_rating,
        "def_rating": def_rating,
        "net_rating": net_rating,
        "pace": pace,
        "ts_pct": ts_pct,
        "efg_pct": efg_pct,
        "three_point_rate": three_point_rate,
        "ftr": ftr,
        "oreb_rate": oreb_rate,
        "turnover_rate": turnover_rate,
        "assist_rate": assist_rate,
        "transition_rate": transition_rate,
        "paint_pressure_proxy": paint_pressure_proxy,
    }


def _percentile(values: List[Optional[float]], value: Optional[float]) -> Optional[float]:
    clean = [item for item in values if item is not None]
    if not clean or value is None:
        return None
    below = sum(1 for item in clean if item <= value)
    return (below / float(len(clean))) * 100.0


def _metric_note(metric_id: str, team_value: Optional[float], league_reference: Optional[float], higher_better: bool) -> str:
    if team_value is None or league_reference is None:
        return "Directional only until more samples are synced."
    if higher_better:
        if team_value >= league_reference:
            return "Above the league baseline."
        return "Below the league baseline and worth a closer look."
    if team_value <= league_reference:
        return "Below the league baseline in a helpful direction."
    return "Above the league baseline and worth reducing."


def _build_rows(
    metrics: Dict[str, Optional[float]],
    league_avgs: Dict[str, Optional[float]],
    league_values: Dict[str, List[Optional[float]]],
    recent_metrics: Optional[Dict[str, Optional[float]]] = None,
) -> List[StyleMetricRow]:
    rows: List[StyleMetricRow] = []
    for metric_id, label, higher_better, _fmt in _STYLE_METRICS:
        team_value = metrics.get(metric_id)
        league_reference = league_avgs.get(metric_id)
        percentile = _percentile(league_values.get(metric_id, []), team_value)
        row = StyleMetricRow(
            metric_id=metric_id,
            label=label,
            team_value=_safe_round(team_value, 2),
            league_reference=_safe_round(league_reference, 2),
            percentile=_safe_round(percentile, 1),
            note=_metric_note(metric_id, team_value, league_reference, higher_better),
        )
        if recent_metrics is not None:
            recent_value = recent_metrics.get(metric_id)
            row.recent_value = _safe_round(recent_value, 2)
            if team_value is not None and recent_value is not None:
                row.recent_delta = _safe_round(recent_value - team_value, 2)
        rows.append(row)
    return rows


def _build_comparison_rows(
    metrics_a: Dict[str, Optional[float]],
    metrics_b: Dict[str, Optional[float]],
) -> List[ComparisonMetricRow]:
    rows: List[ComparisonMetricRow] = []
    for metric_id, label, higher_better, fmt in _STYLE_METRICS:
        a_value = metrics_a.get(metric_id)
        b_value = metrics_b.get(metric_id)
        if a_value is None or b_value is None or abs(a_value - b_value) < 1e-9:
            edge = "even"
        elif higher_better:
            edge = "entity_a" if a_value > b_value else "entity_b"
        else:
            edge = "entity_a" if a_value < b_value else "entity_b"
        rows.append(
            ComparisonMetricRow(
                stat_id=metric_id,
                label=label,
                entity_a_value=_safe_round(a_value, 2),
                entity_b_value=_safe_round(b_value, 2),
                higher_better=higher_better,
                format=fmt,
                edge=edge,
            )
        )
    return rows


def _build_style_story(metric_id: str, metrics_a: Dict[str, Optional[float]], metrics_b: Dict[str, Optional[float]]) -> Optional[ComparisonStory]:
    a_value = metrics_a.get(metric_id)
    b_value = metrics_b.get(metric_id)
    if a_value is None or b_value is None or abs(a_value - b_value) < 1e-9:
        return None
    if metric_id == "pace":
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Faster tempo team"
        summary = "The faster team is more likely to drag the matchup toward its preferred pace."
    elif metric_id == "three_point_rate":
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Three-point pressure edge"
        summary = "The higher three-point team should shape shot selection and spacing in this matchup."
    elif metric_id == "turnover_rate":
        winner = "entity_a" if a_value < b_value else "entity_b"
        label = "Cleaner possession profile"
        summary = "The lower turnover team should own more stable offensive possessions."
    elif metric_id == "oreb_rate":
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Stronger glass profile"
        summary = "The stronger offensive-rebound team should create more second-chance margin."
    else:
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Style edge"
        summary = "This matchup exposes a measurable style edge."
    return ComparisonStory(label=label, summary=summary, edge=winner)


def _team_rows(db: Session, team_id: int, season: str) -> List[GameTeamStat]:
    rows = (
        db.query(GameTeamStat)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season, GameTeamStat.team_id == team_id)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )
    return rows


def _all_team_rows(db: Session, season: str) -> Dict[int, List[GameTeamStat]]:
    grouped: Dict[int, List[GameTeamStat]] = defaultdict(list)
    rows = (
        db.query(GameTeamStat)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )
    for row in rows:
        grouped[row.team_id].append(row)
    return grouped


def _opponent_rows(db: Session, season: str, game_ids: List[str], team_id: int) -> Dict[str, GameTeamStat]:
    rows = (
        db.query(GameTeamStat)
        .filter(GameTeamStat.season == season, GameTeamStat.game_id.in_(game_ids), GameTeamStat.team_id != team_id)
        .all()
    )
    return {row.game_id: row for row in rows}


def _team_vector_and_rows(
    db: Session,
    team: Team,
    season: str,
    window: int,
) -> Tuple[Dict[str, Optional[float]], Dict[str, Optional[float]], Dict[str, Optional[float]], List[GameTeamStat], List[GameTeamStat], Dict[str, GameTeamStat], List[str]]:
    season_rows = _team_rows(db, team.id, season)
    if not season_rows:
        raise HTTPException(status_code=404, detail="No team game stats found for {0} in {1}.".format(team.abbreviation, season))
    recent_rows = season_rows[:window] if window else season_rows
    season_game_ids = [row.game_id for row in season_rows]
    recent_game_ids = [row.game_id for row in recent_rows]
    season_opponent_rows = _opponent_rows(db, season, season_game_ids, team.id)
    recent_opponent_rows = _opponent_rows(db, season, recent_game_ids, team.id)
    season_transition = _transition_rate(db, season_game_ids, team.id)
    recent_transition = _transition_rate(db, recent_game_ids, team.id)
    season_metrics = _build_team_vector(db, team, season_rows, season_opponent_rows, season_transition)
    recent_metrics = _build_team_vector(db, team, recent_rows, recent_opponent_rows, recent_transition)
    warnings: List[str] = []
    if len(season_rows) < window:
        warnings.append("Only {0} games were available for the selected window.".format(len(season_rows)))
    if season_transition is None:
        warnings.append("Transition proxy is limited because play-by-play coverage is incomplete.")
    return season_metrics, recent_metrics, season_metrics, season_rows, recent_rows, season_opponent_rows, warnings


def _league_vectors(db: Session, season: str) -> Tuple[Dict[int, Dict[str, Optional[float]]], Dict[int, str], Dict[str, List[Optional[float]]]]:
    all_rows = _all_team_rows(db, season)
    profiles: Dict[int, Dict[str, Optional[float]]] = {}
    team_names: Dict[int, str] = {}
    league_values: Dict[str, List[Optional[float]]] = defaultdict(list)
    for team_id, rows in all_rows.items():
        team = db.query(Team).filter(Team.id == team_id).first()
        if not team:
            continue
        opponent_rows = _opponent_rows(db, season, [row.game_id for row in rows], team_id)
        transition = _transition_rate(db, [row.game_id for row in rows], team_id)
        metrics = _build_team_vector(db, team, rows, opponent_rows, transition)
        profiles[team_id] = metrics
        team_names[team_id] = team.name
        for metric_id, value in metrics.items():
            league_values[metric_id].append(value)
    return profiles, team_names, league_values


def _style_xray_label(metrics: Dict[str, Optional[float]], zscores: Dict[str, float]) -> Tuple[str, str, List[StyleFeatureContributor]]:
    ranked = sorted(
        ((metric_id, abs(zscore)) for metric_id, zscore in zscores.items() if metric_id in {"pace", "three_point_rate", "ftr", "oreb_rate", "turnover_rate", "transition_rate", "paint_pressure_proxy", "ts_pct"}),
        key=lambda item: item[1],
        reverse=True,
    )
    contributors: List[StyleFeatureContributor] = []
    total = sum(score for _, score in ranked[:4]) or 1.0
    for metric_id, score in ranked[:4]:
        contributors.append(
            StyleFeatureContributor(
                metric_id=metric_id,
                label=dict((m[0], m[1]) for m in _STYLE_METRICS).get(metric_id, metric_id),
                value=_safe_round(metrics.get(metric_id), 2),
                share=_safe_round(score / total, 3),
                note="One of the strongest style signals for this team.",
            )
        )

    pace_z = zscores.get("pace", 0.0)
    three_z = zscores.get("three_point_rate", 0.0)
    ftr_z = zscores.get("ftr", 0.0)
    oreb_z = zscores.get("oreb_rate", 0.0)
    tov_z = zscores.get("turnover_rate", 0.0)
    trans_z = zscores.get("transition_rate", 0.0)
    paint_z = zscores.get("paint_pressure_proxy", 0.0)
    ts_z = zscores.get("ts_pct", 0.0)

    if pace_z >= 0.8 and three_z >= 0.7:
        return "Tempo + Spacing", "The team plays faster than average and leans into perimeter volume.", contributors
    if pace_z <= -0.6 and (ftr_z >= 0.7 or paint_z >= 0.7):
        return "Halfcourt Interior Pressure", "The team slows the game and leans into paint/pressure possessions.", contributors
    if tov_z <= -0.7 and ts_z >= 0.4:
        return "Control + Efficiency", "The team protects possessions and converts them into cleaner scoring chances.", contributors
    if trans_z >= 0.7 and pace_z >= 0.5:
        return "Run-and-Pressure", "The team creates an up-tempo game with transition-like possessions.", contributors
    if oreb_z >= 0.7 and three_z <= 0.1:
        return "Glass and Grind", "The team leans on second-chance pressure and slower possessions.", contributors
    return "Balanced", "No single style vector overwhelms the profile, so the team sits near the middle.", contributors


def _neighbor_summary(target: Dict[str, Optional[float]], other: Dict[str, Optional[float]]) -> float:
    keys = [metric_id for metric_id, _, _, _ in _STYLE_METRICS if metric_id not in {"net_rating"}]
    distances = []
    for key in keys:
        tv = target.get(key)
        ov = other.get(key)
        if tv is None or ov is None:
            continue
        distances.append((tv - ov) ** 2)
    return math.sqrt(sum(distances)) if distances else 999.0


def _zscore(values: List[Optional[float]], value: Optional[float]) -> float:
    clean = [item for item in values if item is not None]
    if not clean or value is None:
        return 0.0
    mean = statistics.mean(clean)
    stdev = statistics.pstdev(clean) or 1.0
    return (value - mean) / stdev


def build_team_style_profile(
    db: Session,
    abbr: str,
    season: str,
    window: int = 10,
    opponent_abbr: Optional[str] = None,
) -> TeamStyleProfileResponse:
    team = _fetch_team(db, abbr)
    opponent = _fetch_team(db, opponent_abbr) if opponent_abbr else None
    watermark = _season_watermark(db, season)
    cache_key = _style_cache_key("style_profile", [team.abbreviation, season, str(window), opponent.abbreviation if opponent else "none", watermark])
    cached = CacheManager.get(cache_key)
    if cached:
        return TeamStyleProfileResponse(**cached)

    season_rows = _team_rows(db, team.id, season)
    if not season_rows:
        raise HTTPException(status_code=404, detail="No team game stats found for {0} in {1}.".format(team.abbreviation, season))
    recent_rows = season_rows[:window] if window else season_rows
    all_profiles, team_names, league_values = _league_vectors(db, season)
    if team.id not in all_profiles:
        raise HTTPException(status_code=404, detail="No style profile could be built for {0} in {1}.".format(team.abbreviation, season))

    season_game_ids = [row.game_id for row in season_rows]
    recent_game_ids = [row.game_id for row in recent_rows]
    season_opponent_rows = _opponent_rows(db, season, season_game_ids, team.id)
    recent_opponent_rows = _opponent_rows(db, season, recent_game_ids, team.id)
    season_transition = _transition_rate(db, season_game_ids, team.id)
    recent_transition = _transition_rate(db, recent_game_ids, team.id)
    season_metrics = _build_team_vector(db, team, season_rows, season_opponent_rows, season_transition)
    recent_metrics = _build_team_vector(db, team, recent_rows, recent_opponent_rows, recent_transition)

    league_avgs: Dict[str, Optional[float]] = {}
    for metric_id in league_values.keys():
        metric_list = [item for item in league_values[metric_id] if item is not None]
        league_avgs[metric_id] = statistics.mean(metric_list) if metric_list else None

    current_profile = _build_rows(season_metrics, league_avgs, league_values)
    recent_drift = _build_rows(season_metrics, league_avgs, league_values, recent_metrics=recent_metrics)
    league_context = [
        StyleMetricRow(
            metric_id=metric_id,
            label=label,
            team_value=_safe_round(league_avgs.get(metric_id), 2),
            league_reference=_safe_round(league_avgs.get(metric_id), 2),
            percentile=50.0,
            note="League baseline.",
        )
        for metric_id, label, _higher_better, _fmt in _STYLE_METRICS
    ]

    opponent_comparison: List[ComparisonMetricRow] = []
    warnings: List[str] = []
    if opponent:
        opponent_rows = _team_rows(db, opponent.id, season)
        if opponent_rows:
            opponent_game_ids = [row.game_id for row in opponent_rows]
            opponent_opponent_rows = _opponent_rows(db, season, opponent_game_ids, opponent.id)
            opponent_transition = _transition_rate(db, opponent_game_ids, opponent.id)
            opponent_metrics = _build_team_vector(db, opponent, opponent_rows, opponent_opponent_rows, opponent_transition)
            opponent_comparison = _build_comparison_rows(season_metrics, opponent_metrics)
        else:
            warnings.append("Opponent profile could not be built because season data is sparse.")

    scenario_bins: List[StyleScenarioBin] = []
    pace_values = [value for value in (metrics.get("pace") for metrics in all_profiles.values()) if value is not None]
    net_values = [value for value in (metrics.get("net_rating") for metrics in all_profiles.values()) if value is not None]
    points_values = [value for value in (metrics.get("pts") for metrics in all_profiles.values()) if value is not None]
    if pace_values:
        slow_cut = statistics.quantiles(pace_values, n=4)[0] if len(pace_values) >= 4 else statistics.mean(pace_values)
        fast_cut = statistics.quantiles(pace_values, n=4)[-1] if len(pace_values) >= 4 else statistics.mean(pace_values)
        slow = [profiles for profiles in all_profiles.values() if profiles.get("pace") is not None and profiles["pace"] <= slow_cut]
        middle = [
            profiles
            for profiles in all_profiles.values()
            if profiles.get("pace") is not None and slow_cut < profiles["pace"] < fast_cut
        ]
        fast = [profiles for profiles in all_profiles.values() if profiles.get("pace") is not None and profiles["pace"] >= fast_cut]
        bucket_map = [
            ("Slower", "down", slow, "slower-than-average pace buckets"),
            ("Baseline", "flat", middle, "middle pace buckets"),
            ("Faster", "up", fast, "faster-than-average pace buckets"),
        ]
        for label, direction, bucket, noun in bucket_map:
            bucket_net = [metrics.get("net_rating") for metrics in bucket if metrics.get("net_rating") is not None]
            bucket_pts = [metrics.get("pts") for metrics in bucket if metrics.get("pts") is not None]
            scenario_bins.append(
                StyleScenarioBin(
                    label=label,
                    direction=direction,  # type: ignore[arg-type]
                    sample_size=len(bucket),
                    avg_net_rating=_safe_round(statistics.mean(bucket_net), 2) if bucket_net else None,
                    avg_points_for=_safe_round(statistics.mean(bucket_pts), 2) if bucket_pts else None,
                    summary="Teams in {0} tend to cluster around this outcome profile.".format(noun),
                )
            )
    else:
        warnings.append("Pace buckets could not be computed because too few league samples were available.")

    if len(season_rows) < window:
        warnings.append("Only {0} games were available for the selected window.".format(len(season_rows)))
    if season_transition is None:
        warnings.append("Transition proxy is limited because play-by-play coverage is incomplete.")

    response = TeamStyleProfileResponse(
        team_abbreviation=team.abbreviation,
        team_name=team.name,
        season=season,
        window_games=min(window, len(season_rows)),
        current_profile=current_profile,
        recent_drift=recent_drift,
        league_context=league_context,
        opponent_comparison=opponent_comparison,
        scenario_bins=scenario_bins,
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.dict(), 900)
    return response


def build_style_xray_report(
    db: Session,
    abbr: str,
    season: str,
    window: int = 10,
    opponent_abbr: Optional[str] = None,
) -> StyleXRayResponse:
    team = _fetch_team(db, abbr)
    watermark = _season_watermark(db, season)
    cache_key = _style_cache_key(
        "style_xray",
        [team.abbreviation, season, str(window), opponent_abbr or "none", watermark],
    )
    cached = CacheManager.get(cache_key)
    if cached:
        return StyleXRayResponse(**cached)

    all_profiles, team_names, league_values = _league_vectors(db, season)
    if team.id not in all_profiles:
        raise HTTPException(status_code=404, detail="No style profile could be built for {0} in {1}.".format(team.abbreviation, season))

    current_metrics = all_profiles[team.id]
    recent_report = build_team_style_profile(db=db, abbr=abbr, season=season, window=window, opponent_abbr=opponent_abbr)
    recent_metrics = {row.metric_id: row.recent_value for row in recent_report.recent_drift}
    means: Dict[str, float] = {}
    stds: Dict[str, float] = {}
    for metric_id in current_metrics.keys():
        values = [metrics.get(metric_id) for metrics in all_profiles.values() if metrics.get(metric_id) is not None]
        if values:
            means[metric_id] = statistics.mean(values)
            stds[metric_id] = statistics.pstdev(values) or 1.0
        else:
            means[metric_id] = 0.0
            stds[metric_id] = 1.0
    zscores = {
        metric_id: _zscore([metrics.get(metric_id) for metrics in all_profiles.values()], current_metrics.get(metric_id))
        for metric_id in current_metrics.keys()
    }
    archetype, label_reason, contributors = _style_xray_label(current_metrics, zscores)

    neighbor_rows: List[Tuple[float, int, Dict[str, Optional[float]]]] = []
    for team_id, metrics in all_profiles.items():
        if team_id == team.id:
            continue
        distance = _neighbor_summary(current_metrics, metrics)
        neighbor_rows.append((distance, team_id, metrics))
    neighbor_rows.sort(key=lambda item: item[0])

    nearest_neighbors: List[StyleNeighbor] = []
    for distance, team_id, metrics in neighbor_rows[:5]:
        other_team = db.query(Team).filter(Team.id == team_id).first()
        if not other_team:
            continue
        other_zscores = {
            metric_id: _zscore([metrics2.get(metric_id) for metrics2 in all_profiles.values()], metrics.get(metric_id))
            for metric_id in metrics.keys()
        }
        other_archetype, other_reason, _ = _style_xray_label(metrics, other_zscores)
        nearest_neighbors.append(
            StyleNeighbor(
                team_abbreviation=other_team.abbreviation,
                team_name=other_team.name,
                archetype=other_archetype,
                distance=_safe_round(distance, 3) or 0.0,
                net_rating=_safe_round(metrics.get("net_rating"), 2),
                summary=other_reason,
            )
        )

    adjacent_archetypes: List[StyleNeighbor] = []
    for neighbor in nearest_neighbors:
        if neighbor.archetype != archetype:
            adjacent_archetypes.append(neighbor)
        if len(adjacent_archetypes) >= 3:
            break

    recent_metrics_dict = {metric_id: value for metric_id, value in recent_metrics.items() if value is not None}
    recent_zscores = {
        metric_id: _zscore([metrics.get(metric_id) for metrics in all_profiles.values()], value)
        for metric_id, value in recent_metrics_dict.items()
    }
    recent_archetype, _, _ = _style_xray_label(recent_metrics_dict, recent_zscores)
    if recent_archetype == archetype:
        stability = "stable"
    elif sum(abs(zscores.get(metric_id, 0.0) - recent_zscores.get(metric_id, 0.0)) for metric_id in recent_zscores.keys()) <= 2.0:
        stability = "watch"
    else:
        stability = "shifted"

    warnings: List[str] = []
    if len(nearest_neighbors) < 3:
        warnings.append("Neighbor search is limited because the season sample is small.")
    if recent_report.warnings:
        warnings.extend(recent_report.warnings[:2])

    if not nearest_neighbors:
        data_status = "limited"
    elif warnings:
        data_status = "partial"
    else:
        data_status = "ready"

    scenario_links = [
        StyleScenarioLink(
            scenario_type="reduce_iso_proxy",
            title="Trim live-ball creation risk",
            delta=2.0,
            rationale="Use this when turnover pressure or shaky creation is shaping the archetype.",
            what_if_payload={
                "team": team.abbreviation,
                "season": season,
                "window": str(window),
                "scenario_type": "reduce_iso_proxy",
                "delta": "2.0",
                "opponent": opponent_abbr or "",
            },
        ),
        StyleScenarioLink(
            scenario_type="raise_3pa_rate",
            title="Raise spacing volume",
            delta=0.03,
            rationale="Useful when the archetype is missing enough perimeter pressure to bend help.",
            what_if_payload={
                "team": team.abbreviation,
                "season": season,
                "window": str(window),
                "scenario_type": "raise_3pa_rate",
                "delta": "0.03",
                "opponent": opponent_abbr or "",
            },
        ),
        StyleScenarioLink(
            scenario_type="increase_oreb",
            title="Chase second possessions",
            delta=0.02,
            rationale="Use this when the current style is short on margin-creating second balls.",
            what_if_payload={
                "team": team.abbreviation,
                "season": season,
                "window": str(window),
                "scenario_type": "increase_oreb",
                "delta": "0.02",
                "opponent": opponent_abbr or "",
            },
        ),
    ]
    compare_url = "/compare?mode=styles&team_a={0}&team_b={1}&season={2}".format(
        team.abbreviation,
        opponent_abbr or (nearest_neighbors[0].team_abbreviation if nearest_neighbors else team.abbreviation),
        season,
    )
    prep_url = (
        "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent_abbr, season)
        if opponent_abbr
        else "/teams/{0}?tab=prep&season={1}".format(team.abbreviation, season)
    )

    response = StyleXRayResponse(
        data_status=data_status,  # type: ignore[arg-type]
        canonical_source="warehouse-style-engine",
        team_abbreviation=team.abbreviation,
        team_name=team.name,
        season=season,
        window_games=window,
        archetype=archetype,
        label_reason=label_reason,
        feature_contributors=contributors,
        nearest_neighbors=nearest_neighbors,
        adjacent_archetypes=adjacent_archetypes,
        stability=stability,  # type: ignore[arg-type]
        scenario_links=scenario_links,
        launch_links=StyleLaunchLinks(prep_url=prep_url, compare_url=compare_url),
        source_context={
            "team": team.abbreviation,
            "season": season,
            "opponent": opponent_abbr or "",
        },
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.dict(), 900)
    return response


@router.get("/teams/{abbr}", response_model=TeamStyleProfileResponse)
def get_team_style_profile(
    abbr: str,
    season: str = Query("2025-26"),
    window: int = Query(10, ge=3, le=30),
    opponent: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return build_team_style_profile(db=db, abbr=abbr, season=season, window=window, opponent_abbr=opponent)


@router.get("/xray", response_model=StyleXRayResponse)
def get_style_xray(
    team: str = Query(...),
    season: str = Query("2025-26"),
    window: int = Query(10, ge=3, le=30),
    opponent: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return build_style_xray_report(db=db, abbr=team, season=season, window=window, opponent_abbr=opponent)
