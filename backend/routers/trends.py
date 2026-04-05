from __future__ import annotations

import statistics
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from data.cache import CacheManager
from db.database import get_db
from db.models import GameTeamStat, Team, WarehouseGame
from models.trends import (
    TrendCard,
    TrendCardsResponse,
    TrendSeriesPoint,
    WhatIfComparablePattern,
    WhatIfContext,
    WhatIfDriverFeature,
    WhatIfLaunchLinks,
    WhatIfRequest,
    WhatIfResponse,
    WhatIfStyleImplication,
)
from routers.styles import build_style_xray_report, build_team_style_profile
from services.team_rotation_service import build_team_rotation_report

router = APIRouter()
scenarios_router = APIRouter()


def _safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(value, digits)


def _fetch_team(db: Session, abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr))
    return team


def _season_watermark(db: Session, season: str) -> str:
    watermark = db.query(func.max(GameTeamStat.updated_at)).filter(GameTeamStat.season == season).scalar()
    return watermark.isoformat() if watermark else "none"


def _team_rows(db: Session, team_id: int, season: str) -> List[GameTeamStat]:
    return (
        db.query(GameTeamStat)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.season == season, GameTeamStat.team_id == team_id)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )


def _estimate_possessions(row: GameTeamStat) -> Optional[float]:
    possessions = float(row.fga or 0) - float(row.oreb or 0) + float(row.tov or 0) + (0.44 * float(row.fta or 0))
    if possessions <= 0:
        return None
    return possessions


def _per_game_rate(row: GameTeamStat, numerator: str) -> Optional[float]:
    possessions = _estimate_possessions(row)
    if possessions is None:
        return None
    value = float(getattr(row, numerator) or 0.0)
    return value / possessions


def _shot_profile_summary(current: Dict[str, Optional[float]], recent: Dict[str, Optional[float]]) -> str:
    three_delta = (recent.get("three_point_rate") or 0.0) - (current.get("three_point_rate") or 0.0)
    ts_delta = (recent.get("ts_pct") or 0.0) - (current.get("ts_pct") or 0.0)
    if three_delta >= 0.02:
        return "Three-point volume is drifting upward while efficiency is holding or improving."
    if three_delta <= -0.02:
        return "Three-point volume is drifting down, which is changing the shot mix."
    if ts_delta >= 0.02:
        return "Efficiency is trending upward even without a major shot-profile shift."
    if ts_delta <= -0.02:
        return "Efficiency has softened over the recent window."
    return "Shot profile is stable, so the recent window is not showing a major shift."


def _build_series(rows: List[GameTeamStat], metric: str, title: str) -> List[TrendSeriesPoint]:
    series: List[TrendSeriesPoint] = []
    for row in rows[:5][::-1]:
        if metric == "three_point_rate":
            value = _safe_round(float(row.fg3a or 0) / float(row.fga or 1), 3) if row.fga else None
        elif metric == "turnover_rate":
            possessions = _estimate_possessions(row)
            value = _safe_round(float(row.tov or 0) / possessions, 3) if possessions else None
        elif metric == "foul_rate":
            possessions = _estimate_possessions(row)
            value = _safe_round(float(row.pf or 0) / possessions, 3) if possessions else None
        else:
            value = None
        series.append(TrendSeriesPoint(label=title, value=value))
    return series


def build_trend_cards_report(db: Session, team_abbr: str, season: str, window_games: int) -> TrendCardsResponse:
    team = _fetch_team(db, team_abbr)
    watermark = _season_watermark(db, season)
    cache_key = "trend_cards:{0}:{1}:{2}:{3}".format(team.abbreviation, season, window_games, watermark)
    cached = CacheManager.get(cache_key)
    if cached:
        return TrendCardsResponse(**cached)

    rows = _team_rows(db, team.id, season)
    if not rows:
        raise HTTPException(status_code=404, detail="No team game stats found for {0} in {1}.".format(team.abbreviation, season))
    recent_rows = rows[:window_games] if window_games else rows

    style_report = build_team_style_profile(db=db, abbr=team.abbreviation, season=season, window=window_games)
    rotation_report = build_team_rotation_report(db=db, abbr=team.abbreviation, season=season)
    current = {row.metric_id: row.team_value for row in style_report.current_profile}
    recent = {row.metric_id: row.recent_value if row.recent_value is not None else row.team_value for row in style_report.recent_drift}
    cards: List[TrendCard] = []

    shot_series = _build_series(recent_rows, "three_point_rate", "Recent game")
    shot_delta = (recent.get("three_point_rate") or 0.0) - (current.get("three_point_rate") or 0.0)
    cards.append(
        TrendCard(
            card_id="shot-profile-drift",
            title="Shot Profile Drift",
            direction="up" if shot_delta > 0.01 else "down" if shot_delta < -0.01 else "flat",
            magnitude=_safe_round(abs(shot_delta), 3),
            significance="high" if abs(shot_delta) >= 0.03 else "medium" if abs(shot_delta) >= 0.015 else "low",
            summary=_shot_profile_summary(current, recent),
            series=shot_series,
            supporting_stats={
                "season_three_point_rate": current.get("three_point_rate"),
                "recent_three_point_rate": recent.get("three_point_rate"),
                "season_ts_pct": current.get("ts_pct"),
                "recent_ts_pct": recent.get("ts_pct"),
            },
            drilldowns=[
                "/teams/{0}".format(team.abbreviation),
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, team.abbreviation, season),
            ],
        )
    )

    turnover_series = _build_series(recent_rows, "turnover_rate", "Recent game")
    turnover_delta = (recent.get("turnover_rate") or 0.0) - (current.get("turnover_rate") or 0.0)
    cards.append(
        TrendCard(
            card_id="turnover-pressure",
            title="Turnover Pressure",
            direction="up" if turnover_delta < -0.01 else "down" if turnover_delta > 0.01 else "flat",
            magnitude=_safe_round(abs(turnover_delta), 3),
            significance="high" if abs(turnover_delta) >= 0.03 else "medium" if abs(turnover_delta) >= 0.015 else "low",
            summary="The recent window is changing how cleanly the team is getting shots up.",
            series=turnover_series,
            supporting_stats={
                "season_turnover_rate": current.get("turnover_rate"),
                "recent_turnover_rate": recent.get("turnover_rate"),
                "season_off_rating": current.get("off_rating"),
                "recent_off_rating": recent.get("off_rating"),
            },
            drilldowns=[
                "/teams/{0}".format(team.abbreviation),
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, team.abbreviation, season),
            ],
        )
    )

    foul_series = _build_series(recent_rows, "foul_rate", "Recent game")
    foul_delta = ((recent.get("ftr") or 0.0) - (current.get("ftr") or 0.0))
    cards.append(
        TrendCard(
            card_id="foul-trend",
            title="Foul Trend",
            direction="up" if foul_delta > 0.01 else "down" if foul_delta < -0.01 else "flat",
            magnitude=_safe_round(abs(foul_delta), 3),
            significance="high" if abs(foul_delta) >= 0.03 else "medium" if abs(foul_delta) >= 0.015 else "low",
            summary="Free-throw pressure is either building or fading in the recent window.",
            series=foul_series,
            supporting_stats={
                "season_ftr": current.get("ftr"),
                "recent_ftr": recent.get("ftr"),
                "season_paint_pressure_proxy": current.get("paint_pressure_proxy"),
                "recent_paint_pressure_proxy": recent.get("paint_pressure_proxy"),
            },
            drilldowns=[
                "/teams/{0}".format(team.abbreviation),
                "/pre-read?team={0}&opponent={0}&season={1}".format(team.abbreviation, season),
            ],
        )
    )

    rotation_summary = "Starter stability is {0}, and the load leaders are {1}.".format(
        rotation_report.starter_stability,
        ", ".join(row.player_name for row in rotation_report.minute_load_leaders[:3]) or "not yet clear",
    )
    cards.append(
        TrendCard(
            card_id="rotation-drift",
            title="Rotation Drift",
            direction="up" if rotation_report.rotation_risers else "down" if rotation_report.rotation_fallers else "flat",
            magnitude=_safe_round(float(len(rotation_report.rotation_risers) or len(rotation_report.rotation_fallers)), 2),
            significance="medium" if rotation_report.rotation_risers or rotation_report.rotation_fallers else "low",
            summary=rotation_summary,
            series=[
                TrendSeriesPoint(label="recent starters", value=float(len(rotation_report.recent_starters))),
                TrendSeriesPoint(label="minute leaders", value=float(len(rotation_report.minute_load_leaders))),
            ],
            supporting_stats={
                "window_games": float(rotation_report.window_games),
                "starter_stability": 1.0 if "stable" in rotation_report.starter_stability.lower() else 0.0,
            },
            drilldowns=[
                "/teams/{0}".format(team.abbreviation),
                "/games?team={0}&season={1}".format(team.abbreviation, season),
            ],
        )
    )

    bench_summary = "The bench/minute load split is {0}.".format(
        "holding steady" if not rotation_report.rotation_risers and not rotation_report.rotation_fallers else "moving"
    )
    cards.append(
        TrendCard(
            card_id="bench-burden",
            title="Bench Burden",
            direction="up" if rotation_report.rotation_risers else "down" if rotation_report.rotation_fallers else "flat",
            magnitude=_safe_round(float(len(rotation_report.rotation_risers) + len(rotation_report.rotation_fallers)), 2),
            significance="low" if not (rotation_report.rotation_risers or rotation_report.rotation_fallers) else "medium",
            summary=bench_summary,
            series=[
                TrendSeriesPoint(label="recent", value=float(len(rotation_report.rotation_risers))),
                TrendSeriesPoint(label="season", value=float(len(rotation_report.rotation_fallers))),
            ],
            supporting_stats={
                "recent_risers": float(len(rotation_report.rotation_risers)),
                "recent_fallers": float(len(rotation_report.rotation_fallers)),
            },
            drilldowns=[
                "/teams/{0}".format(team.abbreviation),
                "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(team.abbreviation, team.abbreviation, season),
            ],
        )
    )

    warnings: List[str] = []
    if len(rows) < window_games:
        warnings.append("Only {0} games were available for the selected trend window.".format(len(rows)))
    if not recent_rows:
        warnings.append("Trend cards are limited because recent game stats are missing.")

    response = TrendCardsResponse(
        team_abbreviation=team.abbreviation,
        team_name=team.name,
        season=season,
        window_games=min(window_games, len(rows)),
        cards=cards,
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


_SCENARIO_TYPE_ALIASES = {
    "reduce_iso_proxy": "reduce_iso_proxy",
    "reduce_turnovers": "reduce_iso_proxy",
    "increase_pnr_proxy": "increase_pnr_proxy",
    "increase_pnr_handoff_proxy": "increase_pnr_proxy",
    "protect_shot_quality": "increase_pnr_proxy",
    "raise_3pa_rate": "raise_3pa_rate",
    "slow_pace": "slow_pace",
    "change_pace": "slow_pace",
    "increase_oreb": "increase_oreb",
    "increase_oreb_emphasis": "increase_oreb",
    "increase_offensive_rebounding": "increase_oreb",
}


def _normalize_scenario_type(scenario_type: str) -> str:
    normalized = (scenario_type or "").strip().lower()
    return _SCENARIO_TYPE_ALIASES.get(normalized, normalized)


def _scenario_driver_features(
    profile: Dict[str, Optional[float]],
    league_reference: Dict[str, Optional[float]],
    scenario_type: str,
) -> List[WhatIfDriverFeature]:
    mapping = {
        "reduce_iso_proxy": ["turnover_rate", "paint_pressure_proxy", "ts_pct"],
        "increase_pnr_proxy": ["assist_rate", "ts_pct", "three_point_rate"],
        "raise_3pa_rate": ["three_point_rate", "ts_pct", "pace"],
        "slow_pace": ["pace", "turnover_rate", "def_rating"],
        "increase_oreb": ["oreb_rate", "paint_pressure_proxy", "off_rating"],
    }
    features = mapping.get(scenario_type, ["net_rating", "ts_pct", "pace"])
    labels = {
        "turnover_rate": "Turnover Rate",
        "paint_pressure_proxy": "Paint Pressure Proxy",
        "ts_pct": "True Shooting%",
        "assist_rate": "Assist Rate",
        "three_point_rate": "3PA Rate",
        "pace": "Pace",
        "def_rating": "Defensive Rating",
        "oreb_rate": "Offensive Rebound Rate",
        "off_rating": "Offensive Rating",
        "net_rating": "Net Rating",
    }
    rows = []
    for metric in features:
        value = profile.get(metric)
        reference = league_reference.get(metric)
        note = "Directional only until the scenario has deeper synced support."
        if value is not None and reference is not None:
            delta = abs(value - reference)
            if delta >= 3.0:
                note = "This is already far from the league baseline, so a tactical shift could move the game shape meaningfully."
            elif value >= reference:
                note = "This is already above the league baseline, so the recommendation is more about preserving a current edge than inventing one."
            else:
                note = "This sits below the league baseline and is a reasonable bounded lever to test."
        rows.append(
            WhatIfDriverFeature(
                metric_id=metric,
                label=labels.get(metric, metric.replace("_", " ").title()),
                value=_safe_round(value, 3),
                league_reference=_safe_round(reference, 3),
                note=note,
            )
        )
    return rows


def _scenario_label(scenario_type: str) -> str:
    labels = {
        "reduce_iso_proxy": "Reduce turnovers",
        "increase_pnr_proxy": "Protect shot quality",
        "raise_3pa_rate": "Raise 3PA rate",
        "slow_pace": "Change pace",
        "increase_oreb": "Increase offensive rebounding",
    }
    return labels.get(scenario_type, scenario_type.replace("_", " ").title())


def build_what_if_report(db: Session, payload: WhatIfRequest) -> WhatIfResponse:
    team = _fetch_team(db, payload.team)
    scenario_type = _normalize_scenario_type(payload.scenario_type)
    watermark = _season_watermark(db, payload.season)
    cache_key = "what_if:{0}:{1}:{2}:{3}:{4}:{5}:{6}:{7}".format(
        team.abbreviation,
        payload.season,
        scenario_type,
        payload.delta,
        payload.window,
        payload.opponent or "none",
        payload.context.get("source_view", ""),
        watermark,
    )
    cached = CacheManager.get(cache_key)
    if cached:
        return WhatIfResponse(**cached)

    profile = build_team_style_profile(db=db, abbr=team.abbreviation, season=payload.season, window=payload.window, opponent_abbr=payload.opponent)
    xray = build_style_xray_report(
        db=db,
        abbr=team.abbreviation,
        season=payload.season,
        window=payload.window,
        opponent_abbr=payload.opponent,
    )
    current = {row.metric_id: row.team_value for row in profile.current_profile}
    league_reference = {row.metric_id: row.league_reference for row in profile.current_profile}
    if scenario_type not in {"reduce_iso_proxy", "increase_pnr_proxy", "raise_3pa_rate", "slow_pace", "increase_oreb"}:
        warnings = ["Unsupported scenario type '{0}'.".format(payload.scenario_type)]
        return WhatIfResponse(
            data_status="missing",
            canonical_source="warehouse-style-engine",
            context=WhatIfContext(
                team=team.abbreviation,
                season=payload.season,
                window=payload.window,
                opponent=payload.opponent,
                source_view=payload.context.get("source_view"),
                source_snapshot_id=payload.context.get("snapshot_id"),
            ),
            team_abbreviation=team.abbreviation,
            season=payload.season,
            scenario_type=scenario_type,
            scenario_label=_scenario_label(scenario_type),
            delta=payload.delta,
            expected_direction="neutral",
            summary="This scenario type is not supported by the current decision engine.",
            directional_note="Choose one of the bounded scenario levers surfaced in the UI.",
            confidence="low",
            lower_bound=None,
            upper_bound=None,
            driver_features=[],
            comparable_patterns=[],
            style_implication=WhatIfStyleImplication(
                archetype=xray.archetype,
                label_reason=xray.label_reason,
                stability=xray.stability,
                relevant_contributors=[item.label for item in xray.feature_contributors[:3]],
            ),
            launch_links=WhatIfLaunchLinks(
                prep_url="/teams/{0}?tab=prep&season={1}".format(team.abbreviation, payload.season),
                compare_url="/compare?mode=styles&team_a={0}&team_b={0}&season={1}".format(team.abbreviation, payload.season),
                style_xray_url="/insights?tab=whatif&team={0}&season={1}".format(team.abbreviation, payload.season),
            ),
            warnings=warnings,
        )

    base_coefficients = {
        "reduce_iso_proxy": 0.28,
        "increase_pnr_proxy": 0.24,
        "raise_3pa_rate": 0.30,
        "slow_pace": 0.18,
        "increase_oreb": 0.26,
    }
    team_adjustment = 0.0
    if scenario_type == "slow_pace":
        if (current.get("turnover_rate") or 0.0) > (league_reference.get("turnover_rate") or 0.0):
            team_adjustment += 0.08
        if (current.get("pace") or 0.0) > (league_reference.get("pace") or 0.0):
            team_adjustment += 0.05
    elif scenario_type == "raise_3pa_rate":
        team_adjustment += max(0.0, (league_reference.get("three_point_rate") or 0.0) - (current.get("three_point_rate") or 0.0)) * 0.5
    elif scenario_type == "increase_oreb":
        team_adjustment += max(0.0, (league_reference.get("oreb_rate") or 0.0) - (current.get("oreb_rate") or 0.0)) * 0.4
    elif scenario_type == "reduce_iso_proxy":
        team_adjustment += max(0.0, (current.get("turnover_rate") or 0.0) - (league_reference.get("turnover_rate") or 0.0)) * 0.25
    else:
        team_adjustment += max(0.0, (current.get("assist_rate") or 0.0) - (league_reference.get("assist_rate") or 0.0)) * 0.15

    expected_change = (base_coefficients[scenario_type] * payload.delta) + team_adjustment
    if scenario_type == "slow_pace" and (current.get("pace") or 0.0) < (league_reference.get("pace") or 0.0):
        expected_change *= -0.5

    lower_bound = expected_change - max(0.5, abs(expected_change) * 0.5)
    upper_bound = expected_change + max(0.5, abs(expected_change) * 0.5)
    expected_direction = "improve" if expected_change >= 0 else "decline"

    comparable_patterns: List[WhatIfComparablePattern] = []
    for neighbor in xray.nearest_neighbors[:3]:
        comparable_patterns.append(
            WhatIfComparablePattern(
                team_abbreviation=neighbor.team_abbreviation,
                team_name=neighbor.team_name,
                season=payload.season,
                archetype=neighbor.archetype,
                summary=neighbor.summary,
                distance=neighbor.distance,
            )
        )
    confidence = "high" if payload.window >= 10 and len(comparable_patterns) >= 2 else "medium" if payload.window >= 5 else "low"

    driver_features = _scenario_driver_features(current, league_reference, scenario_type)
    warnings: List[str] = []
    if payload.window < 5:
        warnings.append("The scenario window is small, so the recommendation should be read as a bounded prompt rather than a stable tendency.")
    if not comparable_patterns:
        warnings.append("Comparable-pattern support is thin for this scenario, so the confidence stays conservative.")
    directional_note = None
    if payload.opponent and not profile.opponent_comparison:
        directional_note = "Opponent-aware framing is limited because matchup comparison rows are still sparse, so this still leans team-first."
        warnings.append(directional_note)
    elif not payload.opponent:
        directional_note = "No opponent was selected, so this stays as a team-only directional scenario."
    else:
        directional_note = "Opponent context is included as matchup framing, not as a causal forecast."

    if not comparable_patterns:
        data_status = "limited"
    elif warnings:
        data_status = "partial"
    else:
        data_status = "ready"
    scenario_label = _scenario_label(scenario_type)
    style_implication = WhatIfStyleImplication(
        archetype=xray.archetype,
        label_reason=xray.label_reason,
        stability=xray.stability,
        opposing_tension=(
            "The opponent comparison is strong enough to make this matchup-specific."
            if payload.opponent and profile.opponent_comparison
            else None
        ),
        relevant_contributors=[item.label for item in xray.feature_contributors[:3]],
    )
    prep_url = (
        "/pre-read?team={0}&opponent={1}&season={2}".format(team.abbreviation, payload.opponent, payload.season)
        if payload.opponent
        else "/teams/{0}?tab=prep&season={1}".format(team.abbreviation, payload.season)
    )
    compare_target = payload.opponent or (xray.nearest_neighbors[0].team_abbreviation if xray.nearest_neighbors else team.abbreviation)
    compare_url = "/compare?mode=styles&team_a={0}&team_b={1}&season={2}&source_type=what-if&source_id={3}&reason={4}".format(
        team.abbreviation,
        compare_target,
        payload.season,
        scenario_type,
        scenario_label.replace(" ", "+"),
    )
    compare_url = "{0}&return_to={1}".format(
        compare_url,
        "/insights?tab=whatif&team={0}&season={1}{2}".format(
            team.abbreviation,
            payload.season,
            "&opponent={0}".format(payload.opponent) if payload.opponent else "",
        ).replace(" ", "+"),
    )
    summary = "{0} suggests a {1} outcome band of {2} to {3}.".format(
        scenario_label,
        expected_direction,
        _safe_round(lower_bound, 2),
        _safe_round(upper_bound, 2),
    )

    response = WhatIfResponse(
        data_status=data_status,  # type: ignore[arg-type]
        canonical_source="warehouse-style-engine",
        context=WhatIfContext(
            team=team.abbreviation,
            season=payload.season,
            window=payload.window,
            opponent=payload.opponent,
            source_view=payload.context.get("source_view"),
            source_snapshot_id=payload.context.get("snapshot_id"),
        ),
        team_abbreviation=team.abbreviation,
        season=payload.season,
        scenario_type=scenario_type,
        scenario_label=scenario_label,
        delta=payload.delta,
        expected_direction=expected_direction,
        summary=summary,
        directional_note=directional_note,
        confidence=confidence,  # type: ignore[arg-type]
        lower_bound=_safe_round(lower_bound, 2),
        upper_bound=_safe_round(upper_bound, 2),
        driver_features=driver_features,
        comparable_patterns=comparable_patterns,
        style_implication=style_implication,
        launch_links=WhatIfLaunchLinks(
            prep_url=prep_url,
            compare_url=compare_url,
            style_xray_url="/insights?tab=whatif&team={0}&season={1}{2}".format(
                team.abbreviation,
                payload.season,
                "&opponent={0}".format(payload.opponent) if payload.opponent else "",
            ),
        ),
        warnings=warnings,
    )
    CacheManager.set(cache_key, response.model_dump(), 900)
    return response


@router.get("/cards", response_model=TrendCardsResponse)
def get_trend_cards(
    team: str = Query(...),
    season: str = Query("2025-26"),
    window: int = Query(10, ge=3, le=20),
    db: Session = Depends(get_db),
):
    return build_trend_cards_report(db=db, team_abbr=team, season=season, window_games=window)


@scenarios_router.post("/what-if", response_model=WhatIfResponse)
def run_what_if(
    payload: WhatIfRequest,
    db: Session = Depends(get_db),
):
    return build_what_if_report(db=db, payload=payload)
