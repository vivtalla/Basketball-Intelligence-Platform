from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from db.models import GamePlayerStat, GameTeamStat, PlayByPlayEvent, Player, Team, WarehouseGame
from services.intel_math import clamp, safe_round


def _team_lookup(db: Session, team_abbr: str) -> Team:
    team = db.query(Team).filter(Team.abbreviation == team_abbr.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team '{0}' not found.".format(team_abbr))
    return team


def _parse_lineup_key(lineup_key: Optional[str]) -> Set[int]:
    player_ids: Set[int] = set()
    if not lineup_key:
        return player_ids
    for token in lineup_key.split("-"):
        token = token.strip()
        if not token:
            continue
        try:
            player_ids.add(int(token))
        except ValueError:
            continue
    return player_ids


def _team_game_rows(db: Session, team_id: int, season: str) -> List[Tuple[GameTeamStat, WarehouseGame]]:
    return (
        db.query(GameTeamStat, WarehouseGame)
        .join(WarehouseGame, WarehouseGame.game_id == GameTeamStat.game_id)
        .filter(GameTeamStat.team_id == team_id, GameTeamStat.season == season)
        .order_by(WarehouseGame.game_date.desc().nullslast(), GameTeamStat.game_id.desc())
        .all()
    )


def _game_player_ids(db: Session, game_id: str, team_abbr: str) -> Set[int]:
    rows = (
        db.query(GamePlayerStat.player_id)
        .filter(
            GamePlayerStat.game_id == game_id,
            GamePlayerStat.team_abbreviation == team_abbr,
        )
        .all()
    )
    return {int(player_id) for (player_id,) in rows if player_id is not None}


def _game_event_support(db: Session, game_id: str, team_id: int) -> Dict[str, int]:
    rows = (
        db.query(PlayByPlayEvent)
        .filter(PlayByPlayEvent.game_id == game_id)
        .order_by(PlayByPlayEvent.order_index.asc())
        .all()
    )
    shot_events = 0
    turnover_events = 0
    close_window_events = 0
    for row in rows:
        if row.team_id != team_id:
            continue
        if row.action_family == "shot":
            shot_events += 1
        if row.action_family == "turnover":
            turnover_events += 1
        if row.period and row.period >= 4:
            close_window_events += 1
    return {
        "shot_events": shot_events,
        "turnover_events": turnover_events,
        "close_window_events": close_window_events,
    }


def _style_distance(team_a: Optional[Dict[str, Any]], team_b: Optional[Dict[str, Any]]) -> Optional[float]:
    if not team_a or not team_b:
        return None
    a = team_a.get("current_profile") or {}
    b = team_b.get("current_profile") or {}
    features = ["pace", "ts_pct", "three_point_rate", "turnover_rate", "oreb_rate", "ftr", "assist_rate"]
    total = 0.0
    count = 0
    for feature in features:
        av = a.get(feature)
        bv = b.get(feature)
        if av is None or bv is None:
            continue
        total += abs(float(av) - float(bv))
        count += 1
    if not count:
        return None
    return total / float(count)


def build_follow_through_games(
    db: Session,
    source_type: str,
    source_id: str,
    team_abbreviation: str,
    season: str,
    opponent_abbreviation: Optional[str] = None,
    player_ids: Optional[Sequence[int]] = None,
    lineup_key: Optional[str] = None,
    window_games: int = 10,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    team = _team_lookup(db, team_abbreviation)
    rows = _team_game_rows(db, team.id, season)
    if not rows:
        raise HTTPException(status_code=404, detail="No team games found for {0} in {1}.".format(team_abbreviation.upper(), season))

    lineup_players = _parse_lineup_key(lineup_key)
    player_filter = set(player_ids or [])
    candidates: List[Dict[str, Any]] = []

    opponent_context = None
    if context and isinstance(context.get("opponent_context"), dict):
        opponent_context = context["opponent_context"]

    for index, (team_row, game) in enumerate(rows):
        opponent_row = (
            db.query(GameTeamStat)
            .filter(GameTeamStat.game_id == team_row.game_id, GameTeamStat.team_id != team.id)
            .first()
        )
        game_player_ids = _game_player_ids(db, team_row.game_id, team.abbreviation)
        lineup_overlap = 0.0
        if lineup_players:
            lineup_overlap = len(lineup_players.intersection(game_player_ids)) / float(len(lineup_players))
        player_overlap = 0.0
        if player_filter:
            player_overlap = len(player_filter.intersection(game_player_ids)) / float(len(player_filter))

        opponent_match = 0.0
        if opponent_abbreviation and opponent_row and opponent_row.team_abbreviation:
            opponent_match = 1.0 if opponent_row.team_abbreviation.upper() == opponent_abbreviation.upper() else 0.0

        recency = 1.0 - (index / float(max(1, min(len(rows) - 1, window_games * 2))))
        recency = clamp(recency, 0.0, 1.0)

        opponent_style_distance = None
        if opponent_context and context and isinstance(context.get("source_style_context"), dict):
            opponent_style_distance = _style_distance(context.get("source_style_context"), opponent_context)

        event_support = _game_event_support(db, team_row.game_id, team.id)
        support_score = min(1.0, (event_support["close_window_events"] + event_support["shot_events"] + event_support["turnover_events"]) / 20.0)

        signal_magnitude = float(context.get("signal_magnitude", 0.0)) if context else 0.0
        magnitude_score = clamp(signal_magnitude / 10.0, 0.0, 1.0)

        style_match_bonus = 0.0
        if opponent_style_distance is not None:
            style_match_bonus = clamp(1.0 - opponent_style_distance, 0.0, 1.0)

        relevance = (
            0.30 * recency
            + 0.25 * opponent_match
            + 0.20 * max(lineup_overlap, player_overlap)
            + 0.15 * support_score
            + 0.10 * magnitude_score
            + 0.05 * style_match_bonus
        )

        why_bits: List[str] = []
        if opponent_match > 0:
            why_bits.append("same opponent")
        if lineup_overlap > 0.5:
            why_bits.append("lineup overlap")
        elif player_overlap > 0.5:
            why_bits.append("player overlap")
        if support_score >= 0.5:
            why_bits.append("event support")
        if recency >= 0.75:
            why_bits.append("recent game")

        reason = " + ".join(why_bits) if why_bits else "best available follow-through game"

        deep_link_url = "/games/{0}?source={1}&source_id={2}&team={3}&season={4}".format(
            team_row.game_id,
            source_type,
            source_id,
            team.abbreviation,
            season,
        )
        if opponent_abbreviation:
            deep_link_url += "&opponent={0}".format(opponent_abbreviation.upper())

        candidates.append(
            {
                "game_id": team_row.game_id,
                "game_date": game.game_date.isoformat() if game.game_date else None,
                "opponent_abbreviation": opponent_row.team_abbreviation if opponent_row else None,
                "team_score": team_row.pts,
                "opponent_score": opponent_row.pts if opponent_row else None,
                "margin": float(team_row.pts or 0.0) - float(opponent_row.pts or 0.0) if opponent_row else None,
                "why_this_game": reason,
                "relevance_score": safe_round(relevance, 3),
                "supporting_metrics": {
                    "recency": safe_round(recency, 3),
                    "opponent_match": safe_round(opponent_match, 3),
                    "lineup_overlap": safe_round(lineup_overlap, 3),
                    "player_overlap": safe_round(player_overlap, 3),
                    "event_support": event_support,
                    "style_match_bonus": safe_round(style_match_bonus, 3),
                },
                "deep_link_url": deep_link_url,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["relevance_score"] if item["relevance_score"] is not None else 0.0,
            item["game_date"] or "",
        ),
        reverse=True,
    )

    if not candidates:
        return {
            "source_type": source_type,
            "source_id": source_id,
            "team_abbreviation": team.abbreviation,
            "season": season,
            "games": [],
            "warnings": ["No matching games were found for the current follow-through context."],
        }

    return {
        "source_type": source_type,
        "source_id": source_id,
        "team_abbreviation": team.abbreviation,
        "season": season,
        "games": candidates[:5],
        "warnings": [],
    }

