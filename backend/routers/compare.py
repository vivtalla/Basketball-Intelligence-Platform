from __future__ import annotations

from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import LineupStats, Player, PlayerInjury, Team
from models.compare import TeamComparisonResponse
from models.styles import (
    ComparisonMetricRow,
    ComparisonStory,
    LineupComparisonEntity,
    LineupComparisonResponse,
    StyleComparisonEntity,
    StyleComparisonResponse,
)
from routers.styles import build_style_xray_report, build_team_style_profile
from services.compare_service import build_team_comparison_report

router = APIRouter()


# ─── Compare availability ─────────────────────────────────────────────────────


class PlayerAvailabilitySlot(BaseModel):
    player_id: int
    injury_status: str
    injury_type: Optional[str]
    detail: Optional[str]
    return_date: Optional[date]
    report_date: date


class CompareAvailabilityResponse(BaseModel):
    player_a: Optional[PlayerAvailabilitySlot]
    player_b: Optional[PlayerAvailabilitySlot]


def _current_player_availability(
    db: Session, player_id: int, season: str
) -> Optional[PlayerAvailabilitySlot]:
    """Return the player's injury status as of the latest sync, or None if healthy/no data."""
    latest = (
        db.query(PlayerInjury.report_date)
        .filter(PlayerInjury.season == season)
        .order_by(PlayerInjury.report_date.desc())
        .first()
    )
    if not latest:
        return None
    row = (
        db.query(PlayerInjury)
        .filter(
            PlayerInjury.player_id == player_id,
            PlayerInjury.report_date == latest[0],
            PlayerInjury.season == season,
        )
        .first()
    )
    if not row or (row.injury_status or "").strip().lower() == "available":
        return None
    return PlayerAvailabilitySlot(
        player_id=row.player_id,
        injury_status=row.injury_status or "",
        injury_type=row.injury_type,
        detail=row.detail,
        return_date=row.return_date,
        report_date=row.report_date,
    )


@router.get("/player-availability", response_model=CompareAvailabilityResponse)
def compare_player_availability(
    player_a: int = Query(..., description="Player A person_id"),
    player_b: int = Query(..., description="Player B person_id"),
    season: str = Query("2024-25", description="Season string e.g. 2024-25"),
    db: Session = Depends(get_db),
):
    """Return current injury status for both compare players. Null slot = healthy / no data."""
    return CompareAvailabilityResponse(
        player_a=_current_player_availability(db, player_a, season),
        player_b=_current_player_availability(db, player_b, season),
    )


# ─── Style compare metrics ────────────────────────────────────────────────────


_STYLE_COMPARE_METRICS = [
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


def _fetch_lineup(db: Session, lineup_key: str, season: str) -> LineupStats:
    row = (
        db.query(LineupStats)
        .filter(LineupStats.lineup_key == lineup_key, LineupStats.season == season)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Lineup '{0}' was not found for {1}.".format(lineup_key, season))
    return row


def _lineup_player_names(db: Session, lineup_key: str) -> List[str]:
    player_ids: List[int] = []
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
    return [name_map.get(player_id, str(player_id)) for player_id in player_ids]


def _lineup_entity(db: Session, row: LineupStats) -> LineupComparisonEntity:
    team = db.query(Team).filter(Team.id == row.team_id).first() if row.team_id else None
    player_ids = [int(token) for token in row.lineup_key.split("-") if token.strip().isdigit()]
    return LineupComparisonEntity(
        lineup_key=row.lineup_key,
        player_ids=player_ids,
        player_names=_lineup_player_names(db, row.lineup_key),
        team_abbreviation=team.abbreviation if team else None,
        minutes=_safe_round(row.minutes, 1),
        possessions=row.possessions,
        net_rating=_safe_round(row.net_rating, 2),
        ortg=_safe_round(row.ortg, 2),
        drtg=_safe_round(row.drtg, 2),
        plus_minus=_safe_round(row.plus_minus, 2),
    )


def _comparison_row(stat_id: str, label: str, entity_a_value: Optional[float], entity_b_value: Optional[float], higher_better: bool, fmt: str) -> ComparisonMetricRow:
    if entity_a_value is None or entity_b_value is None or abs(entity_a_value - entity_b_value) < 1e-9:
        edge = "even"
    elif higher_better:
        edge = "entity_a" if entity_a_value > entity_b_value else "entity_b"
    else:
        edge = "entity_a" if entity_a_value < entity_b_value else "entity_b"
    return ComparisonMetricRow(
        stat_id=stat_id,
        label=label,
        entity_a_value=_safe_round(entity_a_value, 2),
        entity_b_value=_safe_round(entity_b_value, 2),
        higher_better=higher_better,
        format=fmt,  # type: ignore[arg-type]
        edge=edge,  # type: ignore[arg-type]
    )


def _build_team_source_context(
    source_type: Optional[str],
    source_id: Optional[str],
    team: Optional[str],
    opponent: Optional[str],
    reason: Optional[str],
) -> Optional[Dict[str, str]]:
    context: Dict[str, str] = {}
    if source_type:
        context["source_type"] = source_type
    if source_id:
        context["source_id"] = source_id
    if team:
        context["team"] = team.upper()
    if opponent:
        context["opponent"] = opponent.upper()
    if reason:
        context["reason"] = reason
    return context or None


def _lineup_story(
    label: str,
    summary: str,
    edge: str,
) -> ComparisonStory:
    return ComparisonStory(label=label, summary=summary, edge=edge)  # type: ignore[arg-type]


def build_lineup_comparison_report(
    db: Session,
    lineup_a: str,
    lineup_b: str,
    season: str,
    team_a: Optional[str] = None,
    team_b: Optional[str] = None,
    source_context: Optional[Dict[str, str]] = None,
) -> LineupComparisonResponse:
    row_a = _fetch_lineup(db, lineup_a, season)
    row_b = _fetch_lineup(db, lineup_b, season)
    entity_a = _lineup_entity(db, row_a)
    entity_b = _lineup_entity(db, row_b)

    rows = [
        _comparison_row("minutes", "Minutes", row_a.minutes, row_b.minutes, True, "number"),
        _comparison_row(
            "possessions",
            "Possessions",
            float(row_a.possessions) if row_a.possessions is not None else None,
            float(row_b.possessions) if row_b.possessions is not None else None,
            True,
            "number",
        ),
        _comparison_row("net_rating", "Net Rating", row_a.net_rating, row_b.net_rating, True, "signed"),
        _comparison_row("ortg", "Offensive Rating", row_a.ortg, row_b.ortg, True, "number"),
        _comparison_row("drtg", "Defensive Rating", row_a.drtg, row_b.drtg, False, "number"),
        _comparison_row("plus_minus", "Plus / Minus", row_a.plus_minus, row_b.plus_minus, True, "signed"),
    ]

    stories: List[ComparisonStory] = []
    if row_a.net_rating is not None and row_b.net_rating is not None and abs(row_a.net_rating - row_b.net_rating) >= 2.0:
        winner = "entity_a" if row_a.net_rating > row_b.net_rating else "entity_b"
        team_label = entity_a.team_abbreviation if winner == "entity_a" else entity_b.team_abbreviation
        stories.append(
            _lineup_story(
                "Stronger net-rating lineup",
                "{0} owns the cleaner net-rating baseline and is the better matchup lever.".format(team_label or "One lineup"),
                winner,
            )
        )
    if row_a.ortg is not None and row_b.ortg is not None and abs(row_a.ortg - row_b.ortg) >= 2.0:
        winner = "entity_a" if row_a.ortg > row_b.ortg else "entity_b"
        team_label = entity_a.team_abbreviation if winner == "entity_a" else entity_b.team_abbreviation
        stories.append(
            _lineup_story(
                "Cleaner offensive lineup",
                "{0} is generating better scoring efficiency.".format(team_label or "One lineup"),
                winner,
            )
        )
    if row_a.drtg is not None and row_b.drtg is not None and abs(row_a.drtg - row_b.drtg) >= 2.0:
        winner = "entity_a" if row_a.drtg < row_b.drtg else "entity_b"
        team_label = entity_a.team_abbreviation if winner == "entity_a" else entity_b.team_abbreviation
        stories.append(
            _lineup_story(
                "Tighter defensive lineup",
                "{0} is suppressing opponent scoring more effectively.".format(team_label or "One lineup"),
                winner,
            )
        )
    if row_a.possessions is not None and row_b.possessions is not None and abs(float(row_a.possessions) - float(row_b.possessions)) >= 40:
        winner = "entity_a" if row_a.possessions > row_b.possessions else "entity_b"
        team_label = entity_a.team_abbreviation if winner == "entity_a" else entity_b.team_abbreviation
        stories.append(
            _lineup_story(
                "Larger sample line",
                "{0} has the sturdier sample, so the read is less noisy.".format(team_label or "One lineup"),
                winner,
            )
        )

    response_team = None
    if team_a and team_b and team_a.upper() == team_b.upper():
        response_team = team_a.upper()
    elif team_a and not team_b:
        response_team = team_a.upper()
    elif team_b and not team_a:
        response_team = team_b.upper()
    elif entity_a.team_abbreviation and entity_a.team_abbreviation == entity_b.team_abbreviation:
        response_team = entity_a.team_abbreviation

    return LineupComparisonResponse(
        season=season,
        team=response_team,
        entity_a=entity_a,
        entity_b=entity_b,
        rows=rows,
        stories=stories[:5],
        source_context=source_context,
    )


def _style_rows(metrics_a: Dict[str, Optional[float]], metrics_b: Dict[str, Optional[float]]) -> List[ComparisonMetricRow]:
    rows: List[ComparisonMetricRow] = []
    for metric_id, label, higher_better, fmt in _STYLE_COMPARE_METRICS:
        rows.append(
            _comparison_row(
                metric_id,
                label,
                metrics_a.get(metric_id),
                metrics_b.get(metric_id),
                higher_better,
                fmt,
            )
        )
    return rows


def _style_story(metric_id: str, metrics_a: Dict[str, Optional[float]], metrics_b: Dict[str, Optional[float]]) -> Optional[ComparisonStory]:
    a_value = metrics_a.get(metric_id)
    b_value = metrics_b.get(metric_id)
    if a_value is None or b_value is None or abs(a_value - b_value) < 1e-9:
        return None
    if metric_id == "pace":
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Faster tempo team"
        summary = "The faster team is more likely to pull the game toward its preferred pace."
    elif metric_id == "three_point_rate":
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Spacing edge"
        summary = "The more perimeter-heavy team should bend the shot profile."
    elif metric_id == "turnover_rate":
        winner = "entity_a" if a_value < b_value else "entity_b"
        label = "Cleaner possession profile"
        summary = "The lower-turnover team should own the more stable offense."
    elif metric_id == "oreb_rate":
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Stronger glass profile"
        summary = "The better offensive-rebounding team should win more second chances."
    elif metric_id == "net_rating":
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Cleaner overall profile"
        summary = "The stronger net-rating team owns the clearer season baseline."
    else:
        winner = "entity_a" if a_value > b_value else "entity_b"
        label = "Style edge"
        summary = "This comparison surfaces a measurable style edge."
    return ComparisonStory(label=label, summary=summary, edge=winner)  # type: ignore[arg-type]


def build_style_comparison_report(
    db: Session,
    team_a: str,
    team_b: str,
    season: str,
    window: int = 10,
    source_context: Optional[Dict[str, str]] = None,
) -> StyleComparisonResponse:
    profile_a = build_team_style_profile(db=db, abbr=team_a, season=season, window=window, opponent_abbr=team_b)
    profile_b = build_team_style_profile(db=db, abbr=team_b, season=season, window=window, opponent_abbr=team_a)
    xray_a = build_style_xray_report(db=db, abbr=team_a, season=season, window=window)
    xray_b = build_style_xray_report(db=db, abbr=team_b, season=season, window=window)

    metrics_a = {row.metric_id: row.team_value for row in profile_a.current_profile}
    metrics_b = {row.metric_id: row.team_value for row in profile_b.current_profile}
    rows = _style_rows(metrics_a, metrics_b)

    stories: List[ComparisonStory] = []
    for metric_id in ["pace", "three_point_rate", "turnover_rate", "oreb_rate", "net_rating"]:
        story = _style_story(metric_id, metrics_a, metrics_b)
        if story:
            stories.append(story)

    entity_a = StyleComparisonEntity(
        abbreviation=profile_a.team_abbreviation,
        name=profile_a.team_name,
        season=profile_a.season,
        archetype=xray_a.archetype,
        label_reason=xray_a.label_reason,
        current_profile=profile_a.current_profile,
    )
    entity_b = StyleComparisonEntity(
        abbreviation=profile_b.team_abbreviation,
        name=profile_b.team_name,
        season=profile_b.season,
        archetype=xray_b.archetype,
        label_reason=xray_b.label_reason,
        current_profile=profile_b.current_profile,
    )

    return StyleComparisonResponse(
        season=season,
        entity_a=entity_a,
        entity_b=entity_b,
        rows=rows,
        stories=stories[:5],
        source_context=source_context,
    )


@router.get("/teams", response_model=TeamComparisonResponse)
def compare_teams(
    team_a: str = Query(...),
    team_b: str = Query(...),
    season: str = Query("2024-25"),
    source_type: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return build_team_comparison_report(
        db=db,
        team_a=team_a,
        team_b=team_b,
        season=season,
        source_context=_build_team_source_context(source_type, source_id, team_a, team_b, reason),
    )


@router.get("/lineups", response_model=LineupComparisonResponse)
def compare_lineups(
    lineup_a: str = Query(...),
    lineup_b: str = Query(...),
    season: str = Query("2025-26"),
    team_a: Optional[str] = Query(None),
    team_b: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    source_context = _build_team_source_context(source_type, source_id, team_a or team_b, None, reason) or {}
    source_context["lineup_a"] = lineup_a
    source_context["lineup_b"] = lineup_b
    if team_a:
        source_context["team_a"] = team_a.upper()
    if team_b:
        source_context["team_b"] = team_b.upper()
    return build_lineup_comparison_report(
        db=db,
        lineup_a=lineup_a,
        lineup_b=lineup_b,
        season=season,
        team_a=team_a,
        team_b=team_b,
        source_context=source_context,
    )


@router.get("/styles", response_model=StyleComparisonResponse)
def compare_styles(
    team_a: str = Query(...),
    team_b: str = Query(...),
    season: str = Query("2025-26"),
    window: int = Query(10, ge=3, le=30),
    source_type: Optional[str] = Query(None),
    source_id: Optional[str] = Query(None),
    reason: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    source_context = _build_team_source_context(source_type, source_id, team_a, team_b, reason) or {}
    source_context["team_a"] = team_a.upper()
    source_context["team_b"] = team_b.upper()
    return build_style_comparison_report(
        db=db,
        team_a=team_a,
        team_b=team_b,
        season=season,
        window=window,
        source_context=source_context,
    )
