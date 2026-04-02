from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from db.models import Team, WarehouseGame
from models.schedule import UpcomingScheduleGame
from models.team import TeamUpcomingGameSummary


def _resolve_team(db: Session, team_abbreviation: Optional[str]) -> Optional[Team]:
    if not team_abbreviation:
        return None
    team = db.query(Team).filter(Team.abbreviation == team_abbreviation.upper()).first()
    if not team:
        raise HTTPException(
            status_code=404,
            detail="Team '{0}' not found.".format(team_abbreviation),
        )
    return team


def _base_upcoming_query(
    db: Session,
    season: str,
    today: date,
    team: Optional[Team] = None,
) -> Query:
    query = (
        db.query(WarehouseGame)
        .filter(
            WarehouseGame.season == season,
            WarehouseGame.game_date.isnot(None),
            WarehouseGame.game_date >= today,
            WarehouseGame.status != "final",
        )
    )
    if team:
        query = query.filter(
            or_(
                WarehouseGame.home_team_id == team.id,
                WarehouseGame.away_team_id == team.id,
            )
        )
    return query


def _serialize_game(game: WarehouseGame) -> UpcomingScheduleGame:
    return UpcomingScheduleGame(
        game_id=game.game_id,
        season=game.season,
        game_date=game.game_date,
        status=game.status,
        home_team_abbreviation=game.home_team_abbreviation,
        home_team_name=game.home_team_name,
        away_team_abbreviation=game.away_team_abbreviation,
        away_team_name=game.away_team_name,
    )


def list_upcoming_games(
    db: Session,
    season: str,
    days: int = 7,
    team_abbreviation: Optional[str] = None,
    today: Optional[date] = None,
) -> List[UpcomingScheduleGame]:
    today = today or date.today()
    team = _resolve_team(db, team_abbreviation)
    end_date = today + timedelta(days=max(days - 1, 0))

    rows = (
        _base_upcoming_query(db, season=season, today=today, team=team)
        .filter(WarehouseGame.game_date <= end_date)
        .order_by(WarehouseGame.game_date.asc(), WarehouseGame.game_id.asc())
        .all()
    )
    return [_serialize_game(row) for row in rows]


def get_next_game_for_team(
    db: Session,
    team: Team,
    season: str,
    today: Optional[date] = None,
) -> Optional[TeamUpcomingGameSummary]:
    today = today or date.today()

    row = (
        _base_upcoming_query(db, season=season, today=today, team=team)
        .order_by(WarehouseGame.game_date.asc(), WarehouseGame.game_id.asc())
        .first()
    )
    if not row:
        return None

    is_home = row.home_team_id == team.id
    opponent_abbreviation = row.away_team_abbreviation if is_home else row.home_team_abbreviation
    opponent_name = row.away_team_name if is_home else row.home_team_name
    return TeamUpcomingGameSummary(
        game_id=row.game_id,
        game_date=row.game_date,
        opponent_abbreviation=opponent_abbreviation,
        opponent_name=opponent_name,
        is_home=is_home,
        status=row.status,
    )
