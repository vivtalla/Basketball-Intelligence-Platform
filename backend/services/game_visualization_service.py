from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from db.models import PlayByPlayEvent, Player, PlayerShotChart, Team, WarehouseGame
from models.game import GameVisualizationElement, GameVisualizationResponse, GameVisualizationStep
from services.pbp_service import describe_event_stream_for_game
from services.shot_lab_service import matches_season_type


SHOT_EVENT_TYPES = {"2pt", "3pt"}


def _anchor_for_event(event: PlayByPlayEvent, home_team_id: Optional[int]) -> Tuple[float, float]:
    side = -1.0 if event.team_id == home_team_id else 1.0
    base_z = {
        "rebound": 8.0,
        "turnover": 16.0,
        "foul": 22.0,
        "substitution": 30.0,
        "timeout": 36.0,
    }.get((event.action_type or "").lower(), 14.0)
    return side * 18.0, base_z


def _event_matches(
    event: PlayByPlayEvent,
    player_id: Optional[int],
    period: Optional[int],
    event_type: Optional[str],
    query: Optional[str],
) -> bool:
    if player_id is not None and event.player_id != player_id:
        return False
    if period is not None and event.period != period:
        return False
    if event_type and event_type != "all" and (event.action_type or "").lower() != event_type.lower():
        return False
    if query:
        normalized = query.strip().lower()
        haystack = " ".join(
            filter(
                None,
                [
                    event.description or "",
                    event.action_type or "",
                    event.action_family or "",
                    event.sub_type or "",
                ],
            )
        ).lower()
        if normalized not in haystack:
            return False
    return True


def _load_shot_lookup(
    db: Session,
    season: str,
    game_id: str,
    player_ids: Sequence[int],
) -> Dict[str, dict]:
    season_type = "Playoffs" if matches_season_type(game_id, "Playoffs") else "Regular Season"
    rows = (
        db.query(PlayerShotChart)
        .filter(
            PlayerShotChart.season == season,
            PlayerShotChart.season_type == season_type,
            PlayerShotChart.player_id.in_(list(player_ids)),
        )
        .all()
    ) if player_ids else []

    lookup: Dict[str, dict] = {}
    for row in rows:
        for shot in row.shots or []:
            if shot.get("game_id") != game_id:
                continue
            shot_event_id = shot.get("shot_event_id")
            if shot_event_id:
                lookup[str(shot_event_id)] = shot
    return lookup


def build_game_visualization(
    db: Session,
    game_id: str,
    player_id: Optional[int] = None,
    period: Optional[int] = None,
    event_type: Optional[str] = None,
    query: Optional[str] = None,
    shot_event_id: Optional[str] = None,
    source: Optional[str] = None,
) -> Optional[GameVisualizationResponse]:
    game = db.query(WarehouseGame).filter(WarehouseGame.game_id == game_id).first()
    if game is None:
        return None

    event_stream = describe_event_stream_for_game(db, game_id, warehouse_game=game)

    events = (
        db.query(PlayByPlayEvent)
        .filter(PlayByPlayEvent.game_id == game_id)
        .order_by(PlayByPlayEvent.order_index.asc())
        .all()
    )
    if not events:
        return GameVisualizationResponse(
            game_id=game_id,
            season=game.season,
            shot_event_id=shot_event_id,
            source=source,
            selected_player_id=player_id,
            selected_period=period,
            selected_event_type=event_type,
            selected_query=query,
            data_status=event_stream.data_status,
            completeness_status=event_stream.completeness_status,
            canonical_source=event_stream.canonical_source,
            last_synced_at=event_stream.last_synced_at,
            exact_shot_match=False,
            steps=[],
        )

    player_ids = sorted({event.player_id for event in events if event.player_id is not None})
    players = {
        row.id: row.full_name
        for row in db.query(Player).filter(Player.id.in_(player_ids)).all()
    } if player_ids else {}
    teams = {
        row.id: row.abbreviation
        for row in db.query(Team).filter(Team.id.in_([event.team_id for event in events if event.team_id is not None])).all()
    }
    shot_lookup = _load_shot_lookup(db, game.season, game_id, [player_id] if player_id is not None else player_ids)

    filtered_events = [
        event
        for event in events
        if _event_matches(event, player_id, period, event_type, query)
    ]

    steps: List[GameVisualizationStep] = []
    exact_shot_match = False
    for event in filtered_events:
        elements: List[GameVisualizationElement] = []
        linked_shot = shot_lookup.get(str(event.source_event_id or ""))
        step_exact_match = bool(
            linked_shot
            and shot_event_id
            and str(event.source_event_id or "") == str(shot_event_id)
        )
        if linked_shot:
            elements.append(
                GameVisualizationElement(
                    kind="shot_arc",
                    label=linked_shot.get("action_type") or event.description,
                    exactness="exact",
                    x=float(linked_shot.get("loc_x", 0)) / 10.0,
                    y=0.35,
                    z=max(0.0, float(linked_shot.get("loc_y", 0)) / 10.0),
                    shot_made=bool(linked_shot.get("shot_made")),
                    shot_value=linked_shot.get("shot_value"),
                    team_id=event.team_id,
                    team_abbreviation=teams.get(event.team_id),
                    player_id=event.player_id,
                    player_name=players.get(event.player_id),
                    event_type=event.action_type,
                )
            )
        else:
            anchor_x, anchor_z = _anchor_for_event(event, game.home_team_id)
            elements.append(
                GameVisualizationElement(
                    kind="context_token",
                    label=event.action_family or event.action_type or "Context",
                    exactness="timeline",
                    x=anchor_x,
                    y=0.35,
                    z=anchor_z,
                    team_id=event.team_id,
                    team_abbreviation=teams.get(event.team_id),
                    player_id=event.player_id,
                    player_name=players.get(event.player_id),
                    event_type=event.action_type,
                )
            )
        exact_shot_match = exact_shot_match or step_exact_match
        steps.append(
            GameVisualizationStep(
                action_number=event.action_number or event.order_index,
                order_index=event.order_index,
                source_event_id=event.source_event_id,
                period=event.period,
                clock=event.clock,
                event_type=event.action_type,
                action_family=event.action_family,
                sub_type=event.sub_type,
                description=event.description,
                team_id=event.team_id,
                team_abbreviation=teams.get(event.team_id),
                player_id=event.player_id,
                player_name=players.get(event.player_id),
                home_score=event.score_home,
                away_score=event.score_away,
                exact_shot_match=step_exact_match,
                elements=elements,
            )
        )

    return GameVisualizationResponse(
        game_id=game_id,
        season=game.season,
        shot_event_id=shot_event_id,
        source=source,
        selected_player_id=player_id,
        selected_period=period,
        selected_event_type=event_type,
        selected_query=query,
        data_status=event_stream.data_status,
        completeness_status=event_stream.completeness_status,
        canonical_source=event_stream.canonical_source,
        last_synced_at=event_stream.last_synced_at,
        exact_shot_match=exact_shot_match,
        steps=steps,
    )
