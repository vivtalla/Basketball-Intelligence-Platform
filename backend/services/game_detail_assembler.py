"""Sprint 77 — Game Detail assembler (Engineer EA3).

Single entry point for ``GET /api/games/{game_id}``. Assembles the canonical
:class:`GameDetailResponse` by composing the existing surface builders:

* the legacy box-score / timeline / top-players walk (was inline in
  ``routers/games.py``),
* :func:`services.game_trajectory_service.compute_win_probability`
  (Engineer EA1),
* :func:`services.game_trajectory_service.compute_lead_tracker` (EA1),
* :func:`services.possession_diary_service.compute_possession_diary`
  (Engineer EA2),
* :func:`services.possession_diary_service.compute_player_quarter_plus_minus`
  (EA2),
* :func:`services.playoff_simulator_service.compute_series_odds_history`
  (Engineer EA3) — only when the underlying ``GameLog`` row carries a
  ``series_id`` (Sprint 73 schema).

Each derived component is wrapped in ``try/except + log.warning`` so a single
failing component never kills the response. The base box-score walk still
raises 404 when the game or PBP is missing, matching the prior route
contract.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GameLog, PlayByPlay, PlayByPlayEvent, Player, Team
from models.game import (
    GameDetailResponse,
    GameEvent,
    GamePlayerSummary,
    GameTimelinePoint,
)
from services.game_trajectory_service import (
    compute_lead_tracker,
    compute_win_probability,
)
from services.pbp_service import describe_event_stream_for_game
from services.playoff_simulator_service import compute_series_odds_history
from services.possession_diary_service import (
    compute_player_quarter_plus_minus,
    compute_possession_diary,
)

logger = logging.getLogger(__name__)


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _build_base_game_detail(db: Session, game_id: str) -> GameDetailResponse:
    """Build the legacy ``GameDetailResponse`` (timeline + top players +
    events) without any of the Sprint 77 derived fields.

    Raises:
        HTTPException: 404 if the game or its PBP is missing — matching the
            historical route behavior.
    """
    game = db.query(GameLog).filter_by(game_id=game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found.")

    event_stream = describe_event_stream_for_game(db, game_id)

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
        raise HTTPException(
            status_code=404, detail=f"No play-by-play found for game {game_id}."
        )

    teams = {
        team.id: team
        for team in db.query(Team)
        .filter(Team.id.in_([game.home_team_id, game.away_team_id]))
        .all()
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
                    action_number=event.action_number
                    or getattr(event, "order_index", 0),
                    period=event.period,
                    clock=event.clock,
                    home_score=score_home,
                    away_score=score_away,
                    scoring_team_id=event.team_id,
                    scoring_team_abbreviation=team.abbreviation if team else None,
                    description=event.description,
                )
            )

        player_name = (
            players.get(event.player_id).full_name
            if event.player_id in players
            else None
        )
        event_rows.append(
            GameEvent(
                action_number=event.action_number
                or getattr(event, "order_index", 0),
                order_index=getattr(event, "order_index", None),
                source_event_id=getattr(event, "source_event_id", None)
                if using_warehouse_events
                else str(event.action_number),
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
                team_abbreviation=teams.get(player.team_id).abbreviation
                if player.team_id in teams
                else None,
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
        data_status=event_stream.data_status,
        completeness_status=event_stream.completeness_status,
        canonical_source=event_stream.canonical_source,
        last_synced_at=event_stream.last_synced_at,
        timeline=timeline,
        top_players=top_players,
        events=event_rows,
    )


def assemble_game_detail(db: Session, game_id: str) -> GameDetailResponse:
    """Assemble the full Sprint 77 game-detail response.

    Composes the legacy box-score builder with the EA1/EA2/EA3 derived
    surfaces. Each derived call is independently fault-tolerant: if any one
    raises, the assembler logs a warning and leaves the corresponding field
    ``None`` rather than failing the whole request.

    The base builder still raises 404 if the game or its PBP is missing.
    """
    response = _build_base_game_detail(db, game_id)

    # --- Win probability + lead tracker (EA1) -------------------------------
    try:
        wp_points = compute_win_probability(db, game_id)
        response.win_probability = wp_points or None
    except Exception:  # pragma: no cover — defensive
        logger.warning("compute_win_probability failed for game %s", game_id, exc_info=True)
        response.win_probability = None

    try:
        lead_points = compute_lead_tracker(db, game_id)
        response.lead_tracker = lead_points or None
    except Exception:  # pragma: no cover — defensive
        logger.warning("compute_lead_tracker failed for game %s", game_id, exc_info=True)
        response.lead_tracker = None

    # --- Possession diary + per-quarter +/- (EA2) ---------------------------
    try:
        diary = compute_possession_diary(db, game_id)
        response.possession_diary = diary or None
    except Exception:  # pragma: no cover — defensive
        logger.warning(
            "compute_possession_diary failed for game %s", game_id, exc_info=True
        )
        response.possession_diary = None

    try:
        impact = compute_player_quarter_plus_minus(db, game_id)
        response.player_quarter_impact = impact or None
    except Exception:  # pragma: no cover — defensive
        logger.warning(
            "compute_player_quarter_plus_minus failed for game %s",
            game_id,
            exc_info=True,
        )
        response.player_quarter_impact = None

    # --- Series odds history (EA3) -----------------------------------------
    # Only emit for playoff games whose ``GameLog`` row carries a series_id.
    # Regular-season rows lack the FK and stay ``None``.
    series_id: Optional[str] = None
    try:
        game_row = db.query(GameLog).filter_by(game_id=game_id).first()
        if game_row is not None:
            series_id = getattr(game_row, "series_id", None)
    except Exception:  # pragma: no cover — defensive
        logger.warning(
            "Failed to read GameLog.series_id for game %s", game_id, exc_info=True
        )
        series_id = None

    if series_id:
        try:
            history = compute_series_odds_history(db, series_id)
            response.series_odds_history = history or None
        except Exception:  # pragma: no cover — defensive
            logger.warning(
                "compute_series_odds_history failed for series %s (game %s)",
                series_id,
                game_id,
                exc_info=True,
            )
            response.series_odds_history = None
    else:
        response.series_odds_history = None

    return response
