from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import GameLog, PlayByPlay, PlayByPlayEvent, Player, Team
from models.game import (
    GameDetailResponse,
    GameEvent,
    GamePlayerSummary,
    GameSummaryResponse,
    GameTimelinePoint,
    GameVisualizationResponse,
)
from services.game_visualization_service import build_game_visualization
from services.game_summary_service import get_game_summary

router = APIRouter()


def _safe_int(value, default=0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


@router.get("/{game_id}/summary", response_model=GameSummaryResponse)
def get_game_summary_route(game_id: str, db: Session = Depends(get_db)):
    summary = get_game_summary(db, game_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found.")
    return summary


@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game_detail(game_id: str, db: Session = Depends(get_db)):
    game = db.query(GameLog).filter_by(game_id=game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found.")

    events = (
        db.query(PlayByPlayEvent)
        .filter_by(game_id=game_id)
        .order_by(PlayByPlayEvent.order_index.asc())
        .all()
    )
    using_warehouse_events = True
    if not events:
        using_warehouse_events = False
        events = (
            db.query(PlayByPlay)
            .filter_by(game_id=game_id)
            .order_by(PlayByPlay.action_number.asc())
            .all()
        )
    if not events:
        raise HTTPException(status_code=404, detail=f"No play-by-play found for game {game_id}.")

    teams = {
        team.id: team
        for team in db.query(Team).filter(Team.id.in_([game.home_team_id, game.away_team_id])).all()
    }

    player_ids = sorted({event.player_id for event in events if event.player_id})
    players = {
        player.id: player
        for player in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }

    timeline: List[GameTimelinePoint] = []
    player_accum: Dict[int, Dict[str, int]] = defaultdict(
        lambda: {"pts": 0, "reb": 0, "ast": 0, "stl": 0, "blk": 0, "tov": 0}
    )
    event_rows: List[GameEvent] = []

    for event in events:
        score_home = _safe_int(event.score_home, 0)
        score_away = _safe_int(event.score_away, 0)
        team = teams.get(event.team_id)
        if event.score_home is not None or event.score_away is not None:
            timeline.append(
                GameTimelinePoint(
                    action_number=event.action_number or getattr(event, "order_index", 0),
                    period=event.period,
                    clock=event.clock,
                    home_score=score_home,
                    away_score=score_away,
                    scoring_team_id=event.team_id,
                    scoring_team_abbreviation=team.abbreviation if team else None,
                    description=event.description,
                )
            )

        player_name = players.get(event.player_id).full_name if event.player_id in players else None
        event_rows.append(
            GameEvent(
                action_number=event.action_number or getattr(event, "order_index", 0),
                order_index=getattr(event, "order_index", None),
                source_event_id=getattr(event, "source_event_id", None) if using_warehouse_events else str(event.action_number),
                period=event.period,
                clock=event.clock,
                team_id=event.team_id,
                team_abbreviation=team.abbreviation if team else None,
                player_id=event.player_id,
                player_name=player_name,
                event_type=event.action_type,
                action_family=getattr(event, "action_family", event.action_type),
                sub_type=getattr(event, "sub_type", None),
                description=event.description,
                home_score=event.score_home,
                away_score=event.score_away,
            )
        )

        if not event.player_id:
            continue

        acc = player_accum[event.player_id]
        if event.action_type == "2pt" and event.sub_type == "made":
            acc["pts"] += 2
        elif event.action_type == "3pt" and event.sub_type == "made":
            acc["pts"] += 3
        elif event.action_type == "freethrow" and event.sub_type == "made":
            acc["pts"] += 1
        elif event.action_type == "rebound":
            acc["reb"] += 1
        elif event.action_type == "turnover":
            acc["tov"] += 1

    top_player_ids = sorted(
        player_accum.keys(),
        key=lambda player_id: (
            player_accum[player_id]["pts"],
            player_accum[player_id]["reb"],
            player_accum[player_id]["ast"],
        ),
        reverse=True,
    )[:10]

    top_players: List[GamePlayerSummary] = []
    for player_id in top_player_ids:
        player = players.get(player_id)
        if not player:
            continue
        top_players.append(
            GamePlayerSummary(
                player_id=player_id,
                player_name=player.full_name,
                team_id=player.team_id,
                team_abbreviation=teams.get(player.team_id).abbreviation if player.team_id in teams else None,
                pts=player_accum[player_id]["pts"],
                reb=player_accum[player_id]["reb"],
                ast=player_accum[player_id]["ast"],
                stl=player_accum[player_id]["stl"],
                blk=player_accum[player_id]["blk"],
                tov=player_accum[player_id]["tov"],
                min=None,
                plus_minus=None,
            )
        )

    home_team = teams.get(game.home_team_id)
    away_team = teams.get(game.away_team_id)
    matchup = None
    if away_team and home_team:
        matchup = f"{away_team.abbreviation} @ {home_team.abbreviation}"

    return GameDetailResponse(
        game_id=game.game_id,
        season=game.season,
        game_date=game.game_date.isoformat() if game.game_date else None,
        matchup=matchup,
        home_team_id=game.home_team_id,
        away_team_id=game.away_team_id,
        home_team_name=home_team.name if home_team else None,
        home_team_abbreviation=home_team.abbreviation if home_team else None,
        away_team_name=away_team.name if away_team else None,
        away_team_abbreviation=away_team.abbreviation if away_team else None,
        home_score=game.home_score,
        away_score=game.away_score,
        timeline=timeline,
        top_players=top_players,
        events=event_rows,
    )


@router.get("/{game_id}/visualization", response_model=GameVisualizationResponse)
def get_game_visualization(
    game_id: str,
    shot_event_id: Optional[str] = None,
    player_id: Optional[int] = None,
    period: Optional[int] = None,
    event_type: Optional[str] = None,
    query: Optional[str] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    payload = build_game_visualization(
        db,
        game_id=game_id,
        shot_event_id=shot_event_id,
        player_id=player_id,
        period=period,
        event_type=event_type,
        query=query,
        source=source,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail=f"No visualization payload found for game {game_id}.")
    return payload
