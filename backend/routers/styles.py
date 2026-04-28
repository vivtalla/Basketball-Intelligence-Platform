from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.cache import CacheManager
from db.database import get_db
from db.models import GameTeamStat, PlayByPlayEvent, Team, TeamShootingSplitStat, WarehouseGame
from models.styles import (
    ComparisonMetricRow,
    ComparisonStory,
    LineupComparisonEntity,
    LineupComparisonResponse,
    StyleComparisonEntity,
    StyleComparisonResponse,
    StyleFeatureContributor,
    StyleHistoryPoint,
    StyleFeatureMovement,
    StyleLatentAxis,
    StyleLatentLoading,
    StyleLatentSpace,
    StyleLaunchLinks,
    StyleMetricRow,
    StyleMovement,
    StyleNeighbor,
    StyleShotProfileDriver,
    StyleScenarioLink,
    StyleScenarioBin,
    StyleXRayResponse,
    TeamStyleProfileResponse,
)
from models.trends import ReplayLaunchTarget
from services.reliability_service import principal_components, project_to_components
from services.team_shot_profile_service import (
    attempt_share_text,
    build_team_shot_profile_drivers,
    family_label,
    signed_points_text,
    summarize_neighbor_shot_profile,
)

router = APIRouter()

_SHOOTING_DRIVER_CANDIDATE_FAMILIES = {
    "ShotAreaTeamDashboard",
    "ShotTypeTeamDashboard",
    "Shot8FTTeamDashboard",
    "Shot5FTTeamDashboard",
    "AssitedShotTeamDashboard",
}

_SHOOTING_FAMILY_LABELS = {
    "ShotAreaTeamDashboard": "Shot Area",
    "ShotTypeTeamDashboard": "Shot Type",
    "Shot8FTTeamDashboard": "Shot Distance (8ft)",
    "Shot5FTTeamDashboard": "Shot Distance (5ft)",
    "AssitedShotTeamDashboard": "Assisted Shot",
    "OverallTeamDashboard": "Overall",
}


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
    max_shooting = (
        db.query(func.max(TeamShootingSplitStat.updated_at))
        .filter(TeamShootingSplitStat.season == season)
        .scalar()
    )
    watermark = max([value for value in [max_team, max_pbp, max_shooting] if value is not None], default=None)
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


def _event_identifier(event: PlayByPlayEvent) -> str:
    if event.source_event_id:
        return str(event.source_event_id)
    return str(event.id)


def _opponent_abbreviation(team_id: int, game: WarehouseGame) -> Optional[str]:
    if game.home_team_id == team_id:
        return game.away_team_abbreviation
    if game.away_team_id == team_id:
        return game.home_team_abbreviation
    return None


def _build_style_replay_target(
    db: Session,
    team: Team,
    season: str,
    recent_rows: List[GameTeamStat],
    source_label: str,
    return_to: str,
    reason_prefix: str,
) -> Optional[ReplayLaunchTarget]:
    for row in recent_rows[:5]:
        game = db.query(WarehouseGame).filter(WarehouseGame.game_id == row.game_id).first()
        if game is None:
            continue
        opponent = _opponent_abbreviation(team.id, game)
        game_date = game.game_date.isoformat() if game.game_date else None
        matched_event = (
            db.query(PlayByPlayEvent)
            .filter(
                PlayByPlayEvent.game_id == game.game_id,
                PlayByPlayEvent.team_id == team.id,
                PlayByPlayEvent.action_type.in_(["2pt", "3pt", "rebound"]),
            )
            .order_by(PlayByPlayEvent.order_index.desc())
            .first()
        )
        reason = "{0} review against {1} on {2}.".format(
            reason_prefix,
            opponent or "the recent opponent",
            game_date or "a recent game",
        )
        params = {
            "source": "style-xray",
            "source_surface": "style-xray",
            "source_id": team.abbreviation,
            "source_label": source_label,
            "reason": reason,
            "return_to": return_to,
            "linkage_quality": "derived" if matched_event is not None else "timeline",
            "team": team.abbreviation,
            "season": season,
        }
        focus_event_id = None
        focused_action_number = None
        if matched_event is not None:
            focus_event_id = _event_identifier(matched_event)
            focused_action_number = matched_event.action_number or matched_event.order_index
            params["focus_event_id"] = focus_event_id
            if focused_action_number is not None:
                params["focus_action_number"] = str(focused_action_number)
        deep_link_url = "/games/{0}?{1}".format(game.game_id, urlencode(params))
        return ReplayLaunchTarget(
            source_surface="style-xray",
            source_label=source_label,
            reason=reason,
            target_game_id=game.game_id,
            target_game_date=game_date,
            target_opponent_abbreviation=opponent,
            focus_event_id=focus_event_id,
            focused_action_number=focused_action_number,
            linkage_quality="derived" if matched_event is not None else "timeline",
            deep_link_url=deep_link_url,
        )
    return None


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


def _family_label(split_family: str) -> str:
    return _SHOOTING_FAMILY_LABELS.get(split_family, split_family)


def _attempt_share_text(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{0:.1f}%".format(value * 100.0)


def _pct_text(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{0:.1f}%".format(value * 100.0)


def _signed_points_text(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return "{0}{1:.1f} pts".format("+" if value >= 0 else "", value * 100.0)


def _select_shot_profile_drivers(
    db: Session,
    season: str,
    team_id: int,
) -> Tuple[List[StyleShotProfileDriver], List[Dict[str, Any]]]:
    rows = (
        db.query(TeamShootingSplitStat)
        .filter(
            TeamShootingSplitStat.season == season,
            TeamShootingSplitStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    if not rows:
        return [], []

    overall_attempts: Dict[int, float] = {}
    for row in rows:
        if row.split_family == "OverallTeamDashboard" and row.fga is not None:
            overall_attempts[row.team_id] = float(row.fga)

    by_key: Dict[Tuple[int, str, str], TeamShootingSplitStat] = {
        (row.team_id, row.split_family, row.split_value): row
        for row in rows
    }
    current_candidates: List[Dict[str, Any]] = []
    for row in rows:
        if row.team_id != team_id or row.split_family not in _SHOOTING_DRIVER_CANDIDATE_FAMILIES:
            continue
        team_total = overall_attempts.get(team_id)
        if not team_total or team_total <= 0 or row.fga is None or row.fga < 40:
            continue
        peer_rows = [
            other
            for other in rows
            if other.team_id != team_id
            and other.split_family == row.split_family
            and other.split_value == row.split_value
            and other.fga is not None
            and overall_attempts.get(other.team_id, 0.0) > 0
        ]
        if not peer_rows:
            continue
        attempt_share = float(row.fga) / team_total
        league_attempt_shares = [
            float(other.fga) / overall_attempts[other.team_id]
            for other in peer_rows
            if overall_attempts.get(other.team_id)
        ]
        league_efg_values = [float(other.efg_pct) for other in peer_rows if other.efg_pct is not None]
        if not league_attempt_shares:
            continue
        league_attempt_share = statistics.mean(league_attempt_shares)
        league_efg_pct = statistics.mean(league_efg_values) if league_efg_values else None
        volume_delta = attempt_share - league_attempt_share
        efg_delta = None
        if row.efg_pct is not None and league_efg_pct is not None:
            efg_delta = float(row.efg_pct) - league_efg_pct
        current_candidates.append(
            {
                "key": (row.split_family, row.split_value),
                "split_family": row.split_family,
                "split_value": row.split_value,
                "label": row.label,
                "attempt_share": attempt_share,
                "efg_pct": float(row.efg_pct) if row.efg_pct is not None else None,
                "league_attempt_share": league_attempt_share,
                "league_efg_pct": league_efg_pct,
                "volume_delta": volume_delta,
                "efg_delta": efg_delta,
                "fga": float(row.fga),
                "pct_ast_fgm": float(row.pct_ast_fgm) if row.pct_ast_fgm is not None else None,
                "pct_uast_fgm": float(row.pct_uast_fgm) if row.pct_uast_fgm is not None else None,
                "row": row,
            }
        )

    if not current_candidates:
        return [], []

    selected: List[Dict[str, Any]] = []
    seen = set()
    volume_sorted = sorted(
        current_candidates,
        key=lambda item: (abs(item["volume_delta"]), item["fga"]),
        reverse=True,
    )
    efficiency_sorted = sorted(
        [item for item in current_candidates if item["efg_delta"] is not None],
        key=lambda item: (abs(item["efg_delta"]), item["fga"]),
        reverse=True,
    )
    for candidate_list in (volume_sorted[:2], efficiency_sorted[:2], volume_sorted[2:], efficiency_sorted[2:]):
        for candidate in candidate_list:
            if candidate["key"] in seen:
                continue
            seen.add(candidate["key"])
            selected.append(candidate)
            if len(selected) >= 4:
                break
        if len(selected) >= 4:
            break

    drivers: List[StyleShotProfileDriver] = []
    for candidate in selected:
        volume_delta = candidate["volume_delta"]
        efg_delta = candidate["efg_delta"]
        if efg_delta is not None and abs(efg_delta) >= abs(volume_delta):
            league_delta = efg_delta
        else:
            league_delta = volume_delta
        summary_parts = [
            "{0} shots".format(_family_label(candidate["split_family"])),
            "take {0} of attempts vs league {1}".format(
                _attempt_share_text(candidate["attempt_share"]),
                _attempt_share_text(candidate["league_attempt_share"]),
            ),
        ]
        if candidate["efg_pct"] is not None and candidate["league_efg_pct"] is not None:
            summary_parts.append(
                "and post {0} eFG vs league {1}".format(
                    _pct_text(candidate["efg_pct"]),
                    _pct_text(candidate["league_efg_pct"]),
                )
            )
        drivers.append(
            StyleShotProfileDriver(
                split_family=candidate["split_family"],
                split_value=candidate["split_value"],
                label=candidate["label"],
                attempt_share=_safe_round(candidate["attempt_share"], 3),
                efg_pct=_safe_round(candidate["efg_pct"], 3) if candidate["efg_pct"] is not None else None,
                league_delta=_safe_round(league_delta, 3),
                summary=" ".join(summary_parts) + ".",
            )
        )
    return drivers, selected


def _driver_sentence(driver: StyleShotProfileDriver) -> str:
    delta_text = signed_points_text(driver.league_delta)
    return "{0} ({1}) is a live shot-profile swing at {2}.".format(
        driver.label,
        family_label(driver.split_family),
        delta_text,
    )


def _neighbor_shot_profile_summary(
    current_team_abbr: str,
    neighbor: Team,
    candidate: Dict[str, Any],
    neighbor_row: Optional[TeamShootingSplitStat],
    neighbor_total_attempts: Optional[float],
) -> Optional[str]:
    if not neighbor_row or not neighbor_total_attempts or neighbor_row.fga is None:
        return None
    current_share = candidate["attempt_share"]
    neighbor_share = float(neighbor_row.fga) / neighbor_total_attempts
    share_gap = current_share - neighbor_share
    current_efg = candidate["efg_pct"]
    neighbor_efg = float(neighbor_row.efg_pct) if neighbor_row.efg_pct is not None else None
    efg_gap = None
    if current_efg is not None and neighbor_efg is not None:
        efg_gap = current_efg - neighbor_efg

    if abs(share_gap) <= 0.02 and (efg_gap is None or abs(efg_gap) <= 0.02):
        return "Shared shot-profile note: both teams sit near each other on {0} volume and efficiency.".format(candidate["label"])
    if abs(share_gap) >= (abs(efg_gap) if efg_gap is not None else 0.0):
        return "{0} leans {1} harder into {2} than {3} ({4} vs {5} of attempts).".format(
            current_team_abbr,
            "more" if share_gap > 0 else "less",
            candidate["label"],
            neighbor.abbreviation,
            _attempt_share_text(current_share),
            _attempt_share_text(neighbor_share),
        )
    if efg_gap is not None:
        return "{0} is {1} efficient than {2} on {3} ({4} vs {5} eFG).".format(
            current_team_abbr,
            "more" if efg_gap > 0 else "less",
            neighbor.abbreviation,
            candidate["label"],
            _pct_text(current_efg),
            _pct_text(neighbor_efg),
        )
    return None


def _scenario_from_driver(
    team_abbr: str,
    season: str,
    window: int,
    opponent_abbr: Optional[str],
    candidate: Dict[str, Any],
) -> Optional[StyleScenarioLink]:
    label = str(candidate["label"]).lower()
    split_family = candidate["split_family"]
    volume_delta = float(candidate["volume_delta"] or 0.0)
    efg_delta = candidate["efg_delta"]
    if "assisted" in label or split_family == "AssitedShotTeamDashboard":
        title = "Create cleaner assisted shots"
        rationale = "Shot-profile driver: {0}".format(candidate["label"])
        if candidate.get("pct_ast_fgm") is not None:
            rationale = "{0} assisted share is shaping the profile.".format(candidate["label"])
        return StyleScenarioLink(
            scenario_type="reduce_iso_proxy",
            title=title,
            delta=2.0,
            rationale=rationale,
            what_if_payload={
                "team": team_abbr,
                "season": season,
                "window": str(window),
                "scenario_type": "reduce_iso_proxy",
                "delta": "2.0",
                "opponent": opponent_abbr or "",
            },
        )
    if any(token in label for token in ["corner 3", "above the break 3", "3pt", "3-pt", "backcourt"]):
        return StyleScenarioLink(
            scenario_type="raise_3pa_rate",
            title="Shift more volume to the arc",
            delta=0.03,
            rationale="Shot-profile driver: {0}".format(candidate["label"]),
            what_if_payload={
                "team": team_abbr,
                "season": season,
                "window": str(window),
                "scenario_type": "raise_3pa_rate",
                "delta": "0.03",
                "opponent": opponent_abbr or "",
            },
        )
    if any(token in label for token in ["less than 5 ft", "5-8 ft", "restricted area", "paint", "in the paint"]):
        return StyleScenarioLink(
            scenario_type="increase_oreb",
            title="Chase extra paint possessions",
            delta=0.02,
            rationale="Shot-profile driver: {0}".format(candidate["label"]),
            what_if_payload={
                "team": team_abbr,
                "season": season,
                "window": str(window),
                "scenario_type": "increase_oreb",
                "delta": "0.02",
                "opponent": opponent_abbr or "",
            },
        )
    if volume_delta < 0 or (efg_delta is not None and efg_delta < 0):
        return StyleScenarioLink(
            scenario_type="raise_3pa_rate",
            title="Open cleaner spacing volume",
            delta=0.03,
            rationale="Shot-profile driver: {0}".format(candidate["label"]),
            what_if_payload={
                "team": team_abbr,
                "season": season,
                "window": str(window),
                "scenario_type": "raise_3pa_rate",
                "delta": "0.03",
                "opponent": opponent_abbr or "",
            },
        )
    return None


_STYLE_CONTRIBUTOR_KEYS = {
    "pace",
    "three_point_rate",
    "ftr",
    "oreb_rate",
    "turnover_rate",
    "transition_rate",
    "paint_pressure_proxy",
    "ts_pct",
    "assist_rate",
    "def_rating",
}


def classify_archetype(zscores: Dict[str, float]) -> Tuple[str, str, List[float]]:
    """Classify team archetype from z-scores.

    Returns (archetype, reason, trigger_magnitudes) where trigger_magnitudes is
    the list of |z| values for the rules that fired. Confidence is derived from
    these magnitudes downstream.
    """
    pace_z = zscores.get("pace", 0.0)
    three_z = zscores.get("three_point_rate", 0.0)
    ftr_z = zscores.get("ftr", 0.0)
    oreb_z = zscores.get("oreb_rate", 0.0)
    tov_z = zscores.get("turnover_rate", 0.0)
    trans_z = zscores.get("transition_rate", 0.0)
    paint_z = zscores.get("paint_pressure_proxy", 0.0)
    ts_z = zscores.get("ts_pct", 0.0)
    ast_z = zscores.get("assist_rate", 0.0)
    def_z = zscores.get("def_rating", 0.0)

    # Order matters: more specific archetypes first.
    if ast_z >= 0.6 and three_z >= 0.6 and ts_z >= 0.3:
        return (
            "Spread Pick-and-Roll",
            "Ball movement and perimeter volume combine into an orchestrated spread-PnR identity.",
            [abs(ast_z), abs(three_z), abs(ts_z)],
        )
    if trans_z >= 0.6 and def_z <= -0.5:
        return (
            "Transition Defense Disruptors",
            "Defense forces stops and the team cashes them in transition.",
            [abs(trans_z), abs(def_z)],
        )
    if pace_z >= 0.8 and three_z >= 0.7:
        return (
            "Tempo + Spacing",
            "The team plays faster than average and leans into perimeter volume.",
            [abs(pace_z), abs(three_z)],
        )
    if trans_z >= 0.7 and pace_z >= 0.5:
        return (
            "Run-and-Pressure",
            "The team creates an up-tempo game with transition-like possessions.",
            [abs(trans_z), abs(pace_z)],
        )
    if pace_z <= -0.6 and (ftr_z >= 0.7 or paint_z >= 0.7):
        return (
            "Halfcourt Interior Pressure",
            "The team slows the game and leans into paint/pressure possessions.",
            [abs(pace_z), max(abs(ftr_z), abs(paint_z))],
        )
    if pace_z <= -0.3 and ast_z <= -0.5 and three_z <= 0.2:
        return (
            "Iso-Heavy Halfcourt",
            "Slower tempo with below-average ball movement and limited perimeter diet — possessions lean on individual creation.",
            [abs(pace_z), abs(ast_z)],
        )
    if oreb_z >= 0.7 and three_z <= 0.1:
        return (
            "Glass and Grind",
            "The team leans on second-chance pressure and slower possessions.",
            [abs(oreb_z), abs(three_z)],
        )
    if tov_z <= -0.7 and ts_z >= 0.4:
        return (
            "Control + Efficiency",
            "The team protects possessions and converts them into cleaner scoring chances.",
            [abs(tov_z), abs(ts_z)],
        )
    if def_z <= -0.8:
        return (
            "Defensive Anchor",
            "Elite defensive rating shapes the identity more than any offensive lean.",
            [abs(def_z)],
        )
    return (
        "Balanced",
        "No single style vector overwhelms the profile, so the team sits near the middle.",
        [],
    )


def _archetype_confidence(trigger_magnitudes: List[float]) -> str:
    if not trigger_magnitudes:
        return "low"
    avg = sum(trigger_magnitudes) / float(len(trigger_magnitudes))
    if avg >= 1.0:
        return "high"
    if avg >= 0.6:
        return "medium"
    return "low"


def _style_xray_label(
    metrics: Dict[str, Optional[float]],
    zscores: Dict[str, float],
) -> Tuple[str, str, List[StyleFeatureContributor], str]:
    ranked = sorted(
        (
            (metric_id, abs(zscore))
            for metric_id, zscore in zscores.items()
            if metric_id in _STYLE_CONTRIBUTOR_KEYS
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    contributors: List[StyleFeatureContributor] = []
    total = sum(score for _, score in ranked[:4]) or 1.0
    label_lookup = {m[0]: m[1] for m in _STYLE_METRICS}
    for metric_id, score in ranked[:4]:
        contributors.append(
            StyleFeatureContributor(
                metric_id=metric_id,
                label=label_lookup.get(metric_id, metric_id),
                value=_safe_round(metrics.get(metric_id), 2),
                share=_safe_round(score / total, 3),
                note="One of the strongest style signals for this team.",
            )
        )

    archetype, reason, trigger_magnitudes = classify_archetype(zscores)
    confidence = _archetype_confidence(trigger_magnitudes)
    return archetype, reason, contributors, confidence


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


def classify_neighbor_quality(distance: float, all_distances: List[float]) -> str:
    """Band a neighbor's Euclidean distance against the league-wide distribution.

    `all_distances` is the sorted list of distances from this team to every
    other team. Closest third -> high, middle third -> medium, farthest third
    -> low. Degenerate cases fall back to "medium".
    """
    if not all_distances:
        return "medium"
    sorted_d = sorted(all_distances)
    n = len(sorted_d)
    if n < 3:
        return "high" if distance <= sorted_d[0] else "medium"
    high_cutoff = sorted_d[max(0, n // 3 - 1)]
    medium_cutoff = sorted_d[max(0, (2 * n) // 3 - 1)]
    if distance <= high_cutoff:
        return "high"
    if distance <= medium_cutoff:
        return "medium"
    return "low"


_MOVEMENT_FEATURE_KEYS: List[str] = [
    "pace",
    "three_point_rate",
    "ftr",
    "oreb_rate",
    "turnover_rate",
    "transition_rate",
    "paint_pressure_proxy",
    "ts_pct",
    "assist_rate",
]


def build_style_movement(
    baseline_zscores: Dict[str, float],
    recent_zscores: Dict[str, float],
    drift_archetype: Optional[str],
    archetype: str,
    window_games: int,
) -> StyleMovement:
    """Per-feature z-score deltas between season baseline and recent window."""
    label_lookup = {m[0]: m[1] for m in _STYLE_METRICS}
    features: List[StyleFeatureMovement] = []
    for metric_id in _MOVEMENT_FEATURE_KEYS:
        baseline = baseline_zscores.get(metric_id)
        recent = recent_zscores.get(metric_id)
        if baseline is None or recent is None:
            continue
        delta = recent - baseline
        if abs(delta) < 0.25:
            direction = "stable"
        elif delta > 0:
            direction = "gaining"
        else:
            direction = "fading"
        features.append(
            StyleFeatureMovement(
                metric_id=metric_id,
                label=label_lookup.get(metric_id, metric_id),
                baseline_z=_safe_round(baseline, 2),
                recent_z=_safe_round(recent, 2),
                delta_z=_safe_round(delta, 2),
                direction=direction,  # type: ignore[arg-type]
            )
        )

    movers = sorted(
        [f for f in features if f.direction != "stable"],
        key=lambda f: abs(f.delta_z or 0.0),
        reverse=True,
    )
    if not movers:
        narrative = "Recent window looks stable across the main style vectors."
    else:
        phrases = []
        for feature in movers[:3]:
            sign = "+" if (feature.delta_z or 0.0) > 0 else ""
            phrases.append(
                "{0} {1} ({2}{3} z)".format(
                    feature.label.lower(),
                    feature.direction,
                    sign,
                    feature.delta_z,
                )
            )
        tail = ""
        if drift_archetype and drift_archetype != archetype:
            tail = " — recent window resembles {0}.".format(drift_archetype)
        else:
            tail = "."
        narrative = "Over the last window: " + ", ".join(phrases) + tail

    return StyleMovement(
        narrative=narrative,
        drift_archetype=drift_archetype if drift_archetype and drift_archetype != archetype else None,
        window_games=window_games,
        features=features,
    )


def _record_for_rows(rows: List[GameTeamStat]) -> Optional[str]:
    wins = sum(1 for row in rows if row.won is True)
    losses = sum(1 for row in rows if row.won is False)
    if wins + losses == 0:
        return None
    return "{0}-{1}".format(wins, losses)


def _build_style_history(
    current_rows: List[GameTeamStat],
    team_metrics_for_rows,
    all_profiles: Dict[int, Dict[str, Optional[float]]],
    archetype: str,
    shot_profile_drivers: List[StyleShotProfileDriver],
) -> List[StyleHistoryPoint]:
    if not current_rows:
        return []
    history_windows = [
        ("Last 5", current_rows[:5]),
        ("Last 10", current_rows[:10]),
        ("Season", current_rows),
    ]
    history: List[StyleHistoryPoint] = []
    for label, rows in history_windows:
        if not rows:
            continue
        metrics = team_metrics_for_rows(rows)
        zscores = {
            metric_id: _zscore([profile.get(metric_id) for profile in all_profiles.values()], metrics.get(metric_id))
            for metric_id in metrics.keys()
        }
        point_archetype, _, _, confidence = _style_xray_label(metrics, zscores)
        history.append(
            StyleHistoryPoint(
                label=label,
                archetype=point_archetype,
                confidence=confidence,  # type: ignore[arg-type]
                record=_record_for_rows(rows),
                shot_profile_note=shot_profile_drivers[0].summary if shot_profile_drivers and label != "Season" else None,
            )
        )
    if history and history[-1].archetype != archetype:
        history[-1].archetype = archetype
    return history


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
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


_STYLE_LATENT_TOP_LOADINGS = 3


def _build_style_latent_space(
    profiles: Dict[int, Dict[str, Optional[float]]],
    feature_keys: List[str],
    feature_labels: Dict[str, str],
    subject_team_id: int,
    n_axes: int = 2,
) -> Optional[StyleLatentSpace]:
    """Run PCA over the league's current-season style vectors and project the
    subject team into the resulting latent space.

    Returns None when fewer than `2 * n_features` complete team rows are
    available — the empirical covariance estimate is too noisy below that
    threshold to be coach-readable. Features missing on any team default to
    the league mean (0.0 after centering) so a sparse metric doesn't kill the
    whole latent view.
    """
    complete_rows: List[Tuple[int, List[float]]] = []
    column_means: Dict[str, float] = {}
    for key in feature_keys:
        values = [
            profile.get(key)
            for profile in profiles.values()
            if profile.get(key) is not None
        ]
        column_means[key] = float(statistics.mean(values)) if values else 0.0

    for team_id, profile in profiles.items():
        row: List[float] = []
        for key in feature_keys:
            value = profile.get(key)
            row.append(float(value) if value is not None else column_means[key])
        complete_rows.append((team_id, row))

    n_features = len(feature_keys)
    if len(complete_rows) < max(2 * n_features, 4):
        return None

    vectors = [row for _team_id, row in complete_rows]
    components, eigenvalues, mean_vec = principal_components(
        vectors, k=min(n_axes, n_features)
    )
    total_variance = sum(eigenvalues) or 1.0

    subject_row = next(
        (row for team_id, row in complete_rows if team_id == subject_team_id),
        None,
    )
    if subject_row is None:
        return None
    subject_coords = project_to_components(subject_row, components, mean_vec)

    axes: List[StyleLatentAxis] = []
    for index, component in enumerate(components):
        if eigenvalues[index] <= 1e-9:
            continue
        signed_loadings = [
            (feature_keys[i], component[i]) for i in range(n_features)
        ]
        signed_loadings.sort(key=lambda pair: pair[1], reverse=True)
        top_positive = [
            StyleLatentLoading(
                feature_id=key,
                label=feature_labels.get(key, key),
                loading=round(float(loading), 3),
            )
            for key, loading in signed_loadings[:_STYLE_LATENT_TOP_LOADINGS]
            if loading > 0
        ]
        top_negative = [
            StyleLatentLoading(
                feature_id=key,
                label=feature_labels.get(key, key),
                loading=round(float(loading), 3),
            )
            for key, loading in reversed(signed_loadings[-_STYLE_LATENT_TOP_LOADINGS:])
            if loading < 0
        ]
        axes.append(
            StyleLatentAxis(
                axis="PC{0}".format(index + 1),
                explained_variance_ratio=round(eigenvalues[index] / total_variance, 3),
                subject_coordinate=round(float(subject_coords[index]), 3),
                top_positive=top_positive,
                top_negative=top_negative,
            )
        )

    if not axes:
        return None

    captured_share = round(sum(axis.explained_variance_ratio for axis in axes) * 100.0, 1)
    interpretation = (
        "PC1 + PC2 capture {0}% of league stylistic variation; positive loadings push a team toward that axis, negative loadings pull it away."
    ).format(captured_share)
    return StyleLatentSpace(
        sample_size=len(complete_rows),
        feature_count=n_features,
        axes=axes,
        interpretation=interpretation,
    )


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

    season_rows = _team_rows(db, team.id, season)
    recent_rows = season_rows[:window] if window else season_rows
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
    archetype, label_reason, contributors, archetype_confidence = _style_xray_label(current_metrics, zscores)
    shot_profile_drivers, driver_candidates = build_team_shot_profile_drivers(db, season, team.id)
    actionable_shot_profile_drivers = [driver for driver in shot_profile_drivers if driver.strong_claim]
    if actionable_shot_profile_drivers:
        label_reason = "{0} {1}".format(label_reason, _driver_sentence(actionable_shot_profile_drivers[0]))

    neighbor_rows: List[Tuple[float, int, Dict[str, Optional[float]]]] = []
    for team_id, metrics in all_profiles.items():
        if team_id == team.id:
            continue
        distance = _neighbor_summary(current_metrics, metrics)
        neighbor_rows.append((distance, team_id, metrics))
    neighbor_rows.sort(key=lambda item: item[0])
    all_distances = [row[0] for row in neighbor_rows]

    nearest_neighbors: List[StyleNeighbor] = []
    for distance, team_id, metrics in neighbor_rows[:5]:
        other_team = db.query(Team).filter(Team.id == team_id).first()
        if not other_team:
            continue
        other_zscores = {
            metric_id: _zscore([metrics2.get(metric_id) for metrics2 in all_profiles.values()], metrics.get(metric_id))
            for metric_id in metrics.keys()
        }
        other_archetype, other_reason, _, _ = _style_xray_label(metrics, other_zscores)
        shot_profile_note = None
        for candidate in driver_candidates:
            neighbor_total = None
            neighbor_overall = db.query(TeamShootingSplitStat).filter(
                TeamShootingSplitStat.team_id == other_team.id,
                TeamShootingSplitStat.season == season,
                TeamShootingSplitStat.is_playoff == False,  # noqa: E712
                TeamShootingSplitStat.split_family == "OverallTeamDashboard",
            ).first()
            if neighbor_overall and neighbor_overall.fga is not None:
                neighbor_total = float(neighbor_overall.fga)
            neighbor_row = db.query(TeamShootingSplitStat).filter(
                TeamShootingSplitStat.team_id == other_team.id,
                TeamShootingSplitStat.season == season,
                TeamShootingSplitStat.is_playoff == False,  # noqa: E712
                TeamShootingSplitStat.split_family == candidate["split_family"],
                TeamShootingSplitStat.split_value == candidate["split_value"],
            ).first()
            shot_profile_note = summarize_neighbor_shot_profile(
                team.abbreviation,
                other_team,
                candidate,
                neighbor_row,
                neighbor_total,
            )
            if shot_profile_note:
                break
        matchup_label = None
        if shot_profile_note:
            matchup_label = "Shot-profile mirror" if "Shared shot-profile note" in shot_profile_note else "Shot-profile tension"
        nearest_neighbors.append(
            StyleNeighbor(
                team_abbreviation=other_team.abbreviation,
                team_name=other_team.name,
                archetype=other_archetype,
                distance=_safe_round(distance, 3) or 0.0,
                quality=classify_neighbor_quality(distance, all_distances),  # type: ignore[arg-type]
                net_rating=_safe_round(metrics.get("net_rating"), 2),
                summary=shot_profile_note or other_reason,
                matchup_label=matchup_label,
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
    recent_archetype, _, _, _ = _style_xray_label(recent_metrics_dict, recent_zscores)
    if recent_archetype == archetype:
        stability = "stable"
    elif sum(abs(zscores.get(metric_id, 0.0) - recent_zscores.get(metric_id, 0.0)) for metric_id in recent_zscores.keys()) <= 2.0:
        stability = "watch"
    else:
        stability = "shifted"

    movement = build_style_movement(
        baseline_zscores=zscores,
        recent_zscores=recent_zscores,
        drift_archetype=recent_archetype,
        archetype=archetype,
        window_games=window,
    )

    warnings: List[str] = []
    if len(nearest_neighbors) < 3:
        warnings.append("Neighbor search is limited because the season sample is small.")
    if recent_report.warnings:
        warnings.extend(recent_report.warnings[:2])
    if not shot_profile_drivers:
        warnings.append("Shot-profile drivers are limited because persisted team shooting splits are missing or thin.")
    elif any(driver.trust_level == "caution" for driver in shot_profile_drivers):
        warnings.append("Assisted-shot style reads stay directional only until the official split-family semantics are clearer.")

    if not nearest_neighbors:
        data_status = "limited"
    elif warnings:
        data_status = "partial"
    else:
        data_status = "ready"

    scenario_links: List[StyleScenarioLink] = []
    seen_scenarios = set()
    for candidate in driver_candidates:
        if not candidate.get("strong_claim", True):
            continue
        scenario = _scenario_from_driver(team.abbreviation, season, window, opponent_abbr, candidate)
        if not scenario or scenario.scenario_type in seen_scenarios:
            continue
        scenario_links.append(scenario)
        seen_scenarios.add(scenario.scenario_type)
        if len(scenario_links) >= 3:
            break
    fallback_scenarios = [
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
    for scenario in fallback_scenarios:
        if scenario.scenario_type in seen_scenarios:
            continue
        scenario_links.append(scenario)
        seen_scenarios.add(scenario.scenario_type)
        if len(scenario_links) >= 3:
            break
    compare_url = "/compare?mode=styles&team_a={0}&team_b={1}&season={2}&source_type=style-xray&source_id={0}&reason={3}".format(
        team.abbreviation,
        opponent_abbr or (nearest_neighbors[0].team_abbreviation if nearest_neighbors else team.abbreviation),
        season,
        (actionable_shot_profile_drivers[0].label if actionable_shot_profile_drivers else archetype).replace(" ", "+"),
    )
    compare_url = "{0}&return_to={1}".format(
        compare_url,
        "/insights?tab=xray&team={0}&season={1}{2}".format(
            team.abbreviation,
            season,
            "&opponent={0}".format(opponent_abbr) if opponent_abbr else "",
        ).replace(" ", "+"),
    )
    prep_url = (
        "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, opponent_abbr, season)
        if opponent_abbr
        else "/teams/{0}?tab=prep&season={1}".format(team.abbreviation, season)
    )
    what_if_url = "/insights?tab=whatif&team={0}&season={1}{2}".format(
        team.abbreviation,
        season,
        "&opponent={0}".format(opponent_abbr) if opponent_abbr else "",
    )
    return_to = "/insights?tab=xray&team={0}&season={1}{2}".format(
        team.abbreviation,
        season,
        "&opponent={0}".format(opponent_abbr) if opponent_abbr else "",
    )
    replay_target = _build_style_replay_target(
        db=db,
        team=team,
        season=season,
        recent_rows=season_rows[:window],
        source_label="{0} X-Ray".format(team.abbreviation),
        return_to=return_to,
        reason_prefix=actionable_shot_profile_drivers[0].label if actionable_shot_profile_drivers else archetype,
    )
    history = _build_style_history(
        current_rows=season_rows,
        team_metrics_for_rows=lambda rows: _build_team_vector(
            db,
            team,
            rows,
            _opponent_rows(db, season, [row.game_id for row in rows], team.id),
            _transition_rate(db, [row.game_id for row in rows], team.id),
        ),
        all_profiles=all_profiles,
        archetype=archetype,
        shot_profile_drivers=shot_profile_drivers,
    )

    latent_space = _build_style_latent_space(
        profiles=all_profiles,
        feature_keys=[metric_id for metric_id, _, _, _ in _STYLE_METRICS if metric_id != "net_rating"],
        feature_labels={metric_id: label for metric_id, label, _, _ in _STYLE_METRICS},
        subject_team_id=team.id,
    )

    response = StyleXRayResponse(
        data_status=data_status,  # type: ignore[arg-type]
        canonical_source="warehouse-style-engine",
        team_abbreviation=team.abbreviation,
        team_name=team.name,
        season=season,
        window_games=window,
        archetype=archetype,
        archetype_confidence=archetype_confidence,  # type: ignore[arg-type]
        label_reason=label_reason,
        feature_contributors=contributors,
        nearest_neighbors=nearest_neighbors,
        adjacent_archetypes=adjacent_archetypes,
        shot_profile_drivers=shot_profile_drivers,
        stability=stability,  # type: ignore[arg-type]
        movement=movement,
        history=history,
        scenario_links=scenario_links,
        launch_links=StyleLaunchLinks(
            prep_url=prep_url,
            compare_url=compare_url,
            what_if_url=what_if_url,
            replay_url=replay_target.deep_link_url if replay_target is not None else None,
        ),
        source_context={
            "source_type": "style-xray",
            "team": team.abbreviation,
            "season": season,
            "opponent": opponent_abbr or "",
        },
        replay_target=replay_target,
        warnings=warnings,
        latent_space=latent_space,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
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
