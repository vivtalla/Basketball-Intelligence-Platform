"""Sprint 85 Stream C — Player hustle stats service.

Reads the persisted ``PlayerHustleStat`` row for a single player + season +
season type and returns a flat aggregate. The official league hustle endpoint
returns one row per player per season (no splits), so this surface is a single
panel — no family toggle.

If the row is missing, fall back to ``sync_player_hustle_stats`` to populate
on demand. ``LiveFetchBlockedError`` is swallowed (user-facing read) so the
panel renders an empty state rather than a 500.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from data.nba_client import LiveFetchBlockedError
from db.models import PlayerHustleStat
from services.gravity_sync_service import sync_player_hustle_stats


logger = logging.getLogger(__name__)


def _row_to_dict(row: Optional[PlayerHustleStat]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {
        "team_abbreviation": row.team_abbreviation,
        "gp": row.gp,
        "minutes": row.minutes,
        "contested_shots": row.contested_shots,
        "deflections": row.deflections,
        "charges_drawn": row.charges_drawn,
        "screen_assists": row.screen_assists,
        "screen_assist_points": row.screen_assist_points,
        "loose_balls_recovered": row.loose_balls_recovered,
        "box_outs": row.box_outs,
    }


def _query_row(
    db: Session, player_id: int, season: str, season_type: str
) -> Optional[PlayerHustleStat]:
    return (
        db.query(PlayerHustleStat)
        .filter(
            PlayerHustleStat.player_id == player_id,
            PlayerHustleStat.season == season,
            PlayerHustleStat.season_type == season_type,
        )
        .first()
    )


def get_player_hustle(
    db: Session,
    player_id: int,
    season: str,
    is_playoff: bool = False,
) -> Dict[str, Any]:
    """Return one player's hustle aggregate, syncing on demand if missing.

    Response shape::

        {
            "player_id": int,
            "season": str,
            "is_playoff": bool,
            "stats": { contested_shots, deflections, ... } | null,
        }

    ``stats`` is null when no row exists for this player/season (returns 200
    with an empty payload rather than 404 — the frontend renders a "no data"
    state).
    """
    season_type = "Playoffs" if is_playoff else "Regular Season"
    row = _query_row(db, player_id, season, season_type)

    if row is None:
        try:
            sync_player_hustle_stats(db, season=season, season_type=season_type)
            row = _query_row(db, player_id, season, season_type)
        except LiveFetchBlockedError:
            row = None
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "On-demand player hustle sync failed for %s/%s: %s",
                player_id,
                season,
                exc,
            )
            row = None

    return {
        "player_id": player_id,
        "season": season,
        "is_playoff": is_playoff,
        "stats": _row_to_dict(row),
    }
