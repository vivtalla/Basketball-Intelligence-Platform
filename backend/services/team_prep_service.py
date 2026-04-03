from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import Team, TeamStanding, WarehouseGame
from models.team import TeamPrepQueueItem, TeamPrepQueueResponse
from services.compare_service import build_team_comparison_report
from services.team_availability_service import build_team_availability
from services.team_focus_service import build_team_focus_levers_report


def _is_modern_warehouse_season(season: str) -> bool:
    try:
        return int(season[:4]) >= 2024
    except (TypeError, ValueError):
        return False


def _team_schedule_rows(db: Session, team_id: int, season: str) -> List[WarehouseGame]:
    return (
        db.query(WarehouseGame)
        .filter(
            WarehouseGame.season == season,
            WarehouseGame.game_date.isnot(None),
            or_(WarehouseGame.home_team_id == team_id, WarehouseGame.away_team_id == team_id),
        )
        .order_by(WarehouseGame.game_date.asc(), WarehouseGame.game_id.asc())
        .all()
    )


def _rest_days(schedule_rows: List[WarehouseGame], team_id: int, target_game_id: str) -> Optional[int]:
    target_index = next((index for index, row in enumerate(schedule_rows) if row.game_id == target_game_id), None)
    if target_index is None:
        return None
    current = schedule_rows[target_index]
    if current.game_date is None:
        return None
    previous: Optional[WarehouseGame] = None
    for row in reversed(schedule_rows[:target_index]):
        if row.home_team_id == team_id or row.away_team_id == team_id:
            previous = row
            break
    if previous is None or previous.game_date is None:
        return None
    return max((current.game_date - previous.game_date).days - 1, 0)


def _schedule_pressure(rest_days: Optional[int]) -> str:
    if rest_days is None:
        return "schedule opener"
    if rest_days <= 0:
        return "back-to-back"
    if rest_days == 1:
        return "tight turn"
    return "rested"


def _record_string(standing: Optional[TeamStanding]) -> Optional[str]:
    if standing is None:
        return None
    wins = standing.wins or 0
    losses = standing.losses or 0
    if wins + losses == 0:
        return None
    return "{0}-{1}".format(wins, losses)


def _latest_standing(db: Session, team_id: int, season: str) -> Optional[TeamStanding]:
    return (
        db.query(TeamStanding)
        .filter(TeamStanding.team_id == team_id, TeamStanding.season == season)
        .order_by(TeamStanding.snapshot_date.desc(), TeamStanding.updated_at.desc())
        .first()
    )


def _conference_rank(db: Session, standing: Optional[TeamStanding], season: str) -> Optional[int]:
    if standing is None or not standing.conference:
        return None
    latest_snapshot = (
        db.query(TeamStanding.snapshot_date)
        .filter(TeamStanding.season == season)
        .order_by(TeamStanding.snapshot_date.desc())
        .first()
    )
    if latest_snapshot is None or latest_snapshot[0] is None:
        return None
    conf_rows = (
        db.query(TeamStanding)
        .filter(
            TeamStanding.season == season,
            TeamStanding.snapshot_date == latest_snapshot[0],
            TeamStanding.conference == standing.conference,
        )
        .all()
    )
    conf_rows.sort(key=lambda row: (-(row.wins or 0), row.losses or 0, row.team_id))
    for rank, row in enumerate(conf_rows, start=1):
        if row.team_id == standing.team_id:
            return rank
    return None


def _build_links(team_abbreviation: str, opponent_abbreviation: str, season: str) -> Tuple[str, str, str]:
    pre_read_url = "/pre-read?team={0}&opponent={1}&season={2}".format(
        team_abbreviation,
        opponent_abbreviation,
        season,
    )
    scouting_url = "/pre-read?team={0}&opponent={1}&season={2}&mode=scouting".format(
        team_abbreviation,
        opponent_abbreviation,
        season,
    )
    compare_url = "/compare?mode=teams&team_a={0}&team_b={1}&season={2}".format(
        team_abbreviation,
        opponent_abbreviation,
        season,
    )
    return pre_read_url, scouting_url, compare_url


def _prep_urgency(
    opponent_rank: Optional[int],
    unavailable_count: int,
    questionable_count: int,
    rest_advantage: Optional[int],
) -> Tuple[str, str]:
    signals = 0
    reasons: List[str] = []
    if opponent_rank is not None and opponent_rank <= 4:
        signals += 2
        reasons.append("top-tier opponent")
    if unavailable_count > 0:
        signals += 1
        reasons.append("real availability watch")
    if questionable_count > 1:
        signals += 1
        reasons.append("multiple monitor tags")
    if rest_advantage is not None and rest_advantage < 0:
        signals += 1
        reasons.append("rest disadvantage")
    if signals >= 3:
        return "high", ", ".join(reasons[:2]) or "high-leverage prep spot"
    if signals >= 1:
        return "medium", ", ".join(reasons[:2]) or "some matchup friction"
    return "standard", "stable prep spot"


def build_team_prep_queue(
    db: Session,
    abbr: str,
    season: str,
    days: int = 10,
    today: Optional[date] = None,
) -> TeamPrepQueueResponse:
    team = db.query(Team).filter(Team.abbreviation == abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(abbr))

    today = today or date.today()
    schedule_rows = _team_schedule_rows(db, team.id, season)
    if not _is_modern_warehouse_season(season):
        return TeamPrepQueueResponse(
            team_id=team.id,
            abbreviation=team.abbreviation,
            name=team.name,
            season=season,
            data_status="limited",
            canonical_source="legacy-plus-derived",
            generated_at=datetime.utcnow().isoformat(),
            items=[],
        )

    upcoming_rows = [
        row
        for row in schedule_rows
        if row.game_date is not None and row.game_date >= today and row.status != "final" and (row.game_date - today).days <= max(days - 1, 0)
    ]

    items: List[TeamPrepQueueItem] = []
    for row in upcoming_rows:
        is_home = row.home_team_id == team.id
        opponent_id = row.away_team_id if is_home else row.home_team_id
        opponent_abbreviation = row.away_team_abbreviation if is_home else row.home_team_abbreviation
        opponent_name = row.away_team_name if is_home else row.home_team_name
        if opponent_id is None or not opponent_abbreviation:
            continue

        opponent_schedule = _team_schedule_rows(db, opponent_id, season)
        team_rest = _rest_days(schedule_rows, team.id, row.game_id)
        opponent_rest = _rest_days(opponent_schedule, opponent_id, row.game_id)
        rest_advantage = None
        if team_rest is not None and opponent_rest is not None:
            rest_advantage = team_rest - opponent_rest

        opponent_standing = _latest_standing(db, opponent_id, season)
        availability = build_team_availability(db=db, abbr=opponent_abbreviation, season=season, today=today)

        best_edge_label = None
        best_edge_summary = None
        try:
            comparison = build_team_comparison_report(db=db, team_a=team.abbreviation, team_b=opponent_abbreviation, season=season)
            edge_story = next((story for story in comparison.stories if story.edge == "team_a"), None)
            if edge_story is None and comparison.stories:
                edge_story = comparison.stories[0]
            if edge_story is not None:
                best_edge_label = edge_story.label
                best_edge_summary = edge_story.summary
        except HTTPException:
            best_edge_summary = "Matchup edge needs more local team-game coverage before it can be trusted."

        first_adjustment_label = None
        first_adjustment_summary = None
        try:
            focus_report = build_team_focus_levers_report(db=db, abbr=team.abbreviation, season=season)
            if focus_report.focus_levers:
                first_adjustment_label = focus_report.focus_levers[0].title
                first_adjustment_summary = focus_report.focus_levers[0].summary
        except HTTPException:
            first_adjustment_summary = "Adjustment guidance will appear once more team game stats are available."

        opponent_rank = _conference_rank(db, opponent_standing, season)
        urgency, urgency_reason = _prep_urgency(
            opponent_rank=opponent_rank,
            unavailable_count=availability.unavailable_count,
            questionable_count=availability.questionable_count,
            rest_advantage=rest_advantage,
        )
        headline_parts = [
            "{0} {1}".format("vs" if is_home else "at", opponent_abbreviation),
            best_edge_label.lower() if best_edge_label else None,
            first_adjustment_label.lower() if first_adjustment_label else None,
        ]
        prep_headline = " | ".join(part for part in headline_parts if part)
        pre_read_url, scouting_url, compare_url = _build_links(team.abbreviation, opponent_abbreviation, season)
        items.append(
            TeamPrepQueueItem(
                game_id=row.game_id,
                game_date=row.game_date,
                status=row.status,
                prep_urgency=urgency,
                prep_headline=urgency_reason if prep_headline == "" else "{0} | {1}".format(urgency_reason, prep_headline),
                opponent_abbreviation=opponent_abbreviation,
                opponent_name=opponent_name,
                is_home=is_home,
                opponent_record=_record_string(opponent_standing),
                opponent_conference=opponent_standing.conference if opponent_standing else None,
                opponent_playoff_rank=opponent_rank,
                availability_summary=availability.summary,
                unavailable_count=availability.unavailable_count,
                questionable_count=availability.questionable_count,
                probable_count=availability.probable_count,
                team_rest_days=team_rest,
                opponent_rest_days=opponent_rest,
                rest_advantage=rest_advantage,
                schedule_pressure=_schedule_pressure(team_rest),
                best_edge_label=best_edge_label,
                best_edge_summary=best_edge_summary,
                first_adjustment_label=first_adjustment_label,
                first_adjustment_summary=first_adjustment_summary,
                pre_read_url=pre_read_url,
                scouting_url=scouting_url,
                compare_url=compare_url,
            )
        )

    data_status = "ready" if items else "missing"
    if items and any(
        item.best_edge_label is None or item.first_adjustment_label is None for item in items
    ):
        data_status = "partial"

    return TeamPrepQueueResponse(
        team_id=team.id,
        abbreviation=team.abbreviation,
        name=team.name,
        season=season,
        data_status=data_status,
        canonical_source="warehouse",
        generated_at=datetime.utcnow().isoformat(),
        items=items,
    )
