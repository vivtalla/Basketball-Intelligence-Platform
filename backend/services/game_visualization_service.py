from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from db.models import PlayByPlayEvent, Player, PlayerShotChart, Team, WarehouseGame
from models.game import GameVisualizationElement, GameVisualizationResponse, GameVisualizationStep
from services.pbp_service import describe_event_stream_for_game
from services.shot_lab_service import matches_season_type


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


def _event_action_number(event: PlayByPlayEvent) -> int:
    return event.action_number or event.order_index


def _event_matches_identifier(event: PlayByPlayEvent, event_id: Optional[str]) -> bool:
    if not event_id:
        return False
    if event.source_event_id and str(event.source_event_id) == str(event_id):
        return True
    return str(event.id) == str(event_id)


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


def _build_source_context(
    source: Optional[str],
    source_id: Optional[str],
    source_label: Optional[str],
    reason: Optional[str],
    claim_id: Optional[str],
    clip_anchor_id: Optional[str],
    return_to: Optional[str],
    requested_linkage_quality: Optional[str],
) -> Optional[Dict[str, str]]:
    context = {
        "source": source,
        "source_id": source_id,
        "source_label": source_label,
        "reason": reason,
        "claim_id": claim_id,
        "clip_anchor_id": clip_anchor_id,
        "return_to": return_to,
        "linkage_quality": requested_linkage_quality,
    }
    cleaned = {key: value for key, value in context.items() if value}
    return cleaned or None


def _build_visualization_step(
    event: PlayByPlayEvent,
    game: WarehouseGame,
    teams: Dict[int, str],
    players: Dict[int, str],
    shot_lookup: Dict[str, dict],
    shot_event_id: Optional[str],
    focus_event: Optional[PlayByPlayEvent],
    requested_linkage_quality: Optional[str],
) -> GameVisualizationStep:
    linked_shot = shot_lookup.get(str(event.source_event_id or ""))
    step_exact_match = bool(
        linked_shot
        and shot_event_id
        and str(event.source_event_id or "") == str(shot_event_id)
        and str(linked_shot.get("linkage_mode") or "") == "exact"
    )
    is_focus_event = focus_event is not None and event.order_index == focus_event.order_index
    linkage_quality = "timeline"
    elements: List[GameVisualizationElement] = []

    if linked_shot:
        linkage_mode = str(linked_shot.get("linkage_mode") or "derived")
        linkage_quality = "exact" if linkage_mode == "exact" else "derived"
        elements.append(
            GameVisualizationElement(
                kind="shot_arc",
                label=linked_shot.get("action_type") or event.description,
                exactness="exact" if linkage_mode == "exact" else "inferred",
                linkage_mode=linkage_mode,
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
        if is_focus_event and requested_linkage_quality in {"exact", "derived"}:
            linkage_quality = requested_linkage_quality
            exactness = "exact" if requested_linkage_quality == "exact" else "inferred"
        else:
            exactness = "timeline"
        elements.append(
            GameVisualizationElement(
                kind="context_token",
                label=event.action_family or event.action_type or "Context",
                exactness=exactness,
                linkage_mode=linkage_quality,
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

    return GameVisualizationStep(
        action_number=_event_action_number(event),
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
        linkage_quality=linkage_quality,
        sequence_role="focus" if is_focus_event else None,
        sequence_offset=0 if is_focus_event else None,
        elements=elements,
    )


def _resolve_focus_event(
    events: Sequence[PlayByPlayEvent],
    filtered_events: Sequence[PlayByPlayEvent],
    shot_event_id: Optional[str],
    focus_event_id: Optional[str],
    focus_action_number: Optional[int],
) -> Optional[PlayByPlayEvent]:
    for event in events:
        if focus_event_id and _event_matches_identifier(event, focus_event_id):
            return event
    for event in events:
        if focus_action_number is not None and _event_action_number(event) == focus_action_number:
            return event
    for event in events:
        if shot_event_id and event.source_event_id and str(event.source_event_id) == str(shot_event_id):
            return event
    if filtered_events:
        return filtered_events[0]
    if events:
        return events[0]
    return None


def build_game_visualization(
    db: Session,
    game_id: str,
    player_id: Optional[int] = None,
    period: Optional[int] = None,
    event_type: Optional[str] = None,
    query: Optional[str] = None,
    shot_event_id: Optional[str] = None,
    source: Optional[str] = None,
    source_id: Optional[str] = None,
    source_label: Optional[str] = None,
    reason: Optional[str] = None,
    claim_id: Optional[str] = None,
    clip_anchor_id: Optional[str] = None,
    return_to: Optional[str] = None,
    linkage_quality: Optional[str] = None,
    focus_event_id: Optional[str] = None,
    focus_action_number: Optional[int] = None,
    focus_window: int = 1,
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
    resolved_focus_window = max(1, min(int(focus_window or 1), 4))
    source_context = _build_source_context(
        source,
        source_id,
        source_label,
        reason,
        claim_id,
        clip_anchor_id,
        return_to,
        linkage_quality,
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
            linkage_quality=linkage_quality or "timeline",
            highlighted_event_id=None,
            highlighted_action_number=None,
            focus_event_id=focus_event_id,
            focus_action_number=focus_action_number,
            focus_window=resolved_focus_window,
            focus_steps=[],
            source_context=source_context,
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
    focus_event = _resolve_focus_event(
        events=events,
        filtered_events=filtered_events,
        shot_event_id=shot_event_id,
        focus_event_id=focus_event_id,
        focus_action_number=focus_action_number,
    )

    steps: List[GameVisualizationStep] = []
    exact_shot_match = False
    for event in filtered_events:
        step = _build_visualization_step(
            event=event,
            game=game,
            teams=teams,
            players=players,
            shot_lookup=shot_lookup,
            shot_event_id=shot_event_id,
            focus_event=focus_event,
            requested_linkage_quality=linkage_quality,
        )
        exact_shot_match = exact_shot_match or step.exact_shot_match
        steps.append(step)

    focus_steps: List[GameVisualizationStep] = []
    highlighted_event_id: Optional[str] = None
    highlighted_action_number: Optional[int] = None
    if focus_event is not None:
        focus_index = next(
            (index for index, event in enumerate(events) if event.order_index == focus_event.order_index),
            -1,
        )
        if focus_index >= 0:
            start_index = max(0, focus_index - resolved_focus_window)
            end_index = min(len(events), focus_index + resolved_focus_window + 1)
            for index, event in enumerate(events[start_index:end_index], start=start_index):
                step = _build_visualization_step(
                    event=event,
                    game=game,
                    teams=teams,
                    players=players,
                    shot_lookup=shot_lookup,
                    shot_event_id=shot_event_id,
                    focus_event=focus_event,
                    requested_linkage_quality=linkage_quality,
                )
                step.sequence_offset = index - focus_index
                step.sequence_role = "focus" if index == focus_index else "neighbor"
                focus_steps.append(step)
                exact_shot_match = exact_shot_match or step.exact_shot_match
            highlighted_action_number = _event_action_number(focus_event)
            highlighted_event_id = (
                str(focus_event.source_event_id)
                if focus_event.source_event_id
                else focus_event_id
            )

    focus_step = next((step for step in focus_steps if step.sequence_role == "focus"), None)
    resolved_linkage_quality = (
        focus_step.linkage_quality
        if focus_step is not None
        else linkage_quality
        if linkage_quality in {"exact", "derived", "timeline"}
        else "timeline"
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
        linkage_quality=resolved_linkage_quality,
        highlighted_event_id=highlighted_event_id,
        highlighted_action_number=highlighted_action_number,
        focus_event_id=highlighted_event_id or focus_event_id,
        focus_action_number=highlighted_action_number or focus_action_number,
        focus_window=resolved_focus_window,
        focus_steps=focus_steps,
        source_context=source_context,
        steps=steps,
    )
