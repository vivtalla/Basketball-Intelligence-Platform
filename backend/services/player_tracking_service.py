"""Sprint 85 Stream C — Player tracking dashboard service.

Reads `PlayerTrackingStat` rows for a single player and groups them into
three families that mirror the NBA stats.com player-tracking dashboards:

- ``Shot Creation`` — touches, drives, paint/close touches, pull-up production
- ``Passing`` — passes made/received, assist context
- ``Shot Defense`` — close-defense distance bucket FGA / FG%

If no rows are persisted for the requested season + season type, the service
calls ``sync_player_tracking_stats`` to fetch + persist on the fly. Any
``LiveFetchBlockedError`` (user-facing read with cache miss) is swallowed and
the empty payload is returned so the frontend can render a "no data" state.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from data.nba_client import LiveFetchBlockedError
from db.models import PlayerTrackingStat
from services.gravity_sync_service import sync_player_tracking_stats


logger = logging.getLogger(__name__)


# Map raw `tracking_family` values produced by `nba_client.get_player_tracking_dashboard`
# onto the public-facing family labels exposed in the API response.
_FAMILY_LABEL_BY_RAW: Dict[str, str] = {
    "shots": "Shot Creation",
    "passing": "Passing",
    "shot_defense": "Shot Defense",
}

# Stable order mirrors the dashboard reading order on the player profile.
PUBLIC_FAMILY_ORDER: List[str] = ["Shot Creation", "Passing", "Shot Defense"]


def _row_to_dict(row: PlayerTrackingStat) -> Dict[str, Any]:
    return {
        "split_key": row.split_key,
        "team_abbreviation": row.team_abbreviation,
        "gp": row.gp,
        "minutes": row.minutes,
        "touches": row.touches,
        "front_court_touches": row.front_court_touches,
        "time_of_possession": row.time_of_possession,
        "drives": row.drives,
        "passes_made": row.passes_made,
        "passes_received": row.passes_received,
        "catch_shoot_fga": row.catch_shoot_fga,
        "catch_shoot_pts": row.catch_shoot_pts,
        "pull_up_fga": row.pull_up_fga,
        "pull_up_pts": row.pull_up_pts,
        "paint_touch_pts": row.paint_touch_pts,
        "close_touch_pts": row.close_touch_pts,
    }


def _query_rows(
    db: Session, player_id: int, season: str, season_type: str
) -> List[PlayerTrackingStat]:
    return (
        db.query(PlayerTrackingStat)
        .filter(
            PlayerTrackingStat.player_id == player_id,
            PlayerTrackingStat.season == season,
            PlayerTrackingStat.season_type == season_type,
        )
        .order_by(PlayerTrackingStat.tracking_family, PlayerTrackingStat.split_key)
        .all()
    )


def get_player_tracking(
    db: Session,
    player_id: int,
    season: str,
    is_playoff: bool = False,
) -> Dict[str, Any]:
    """Return the player tracking dashboard grouped by public family label.

    Response shape::

        {
            "player_id": int,
            "season": str,
            "is_playoff": bool,
            "families": {
                "Shot Creation": [ {split_key, gp, ...}, ... ],
                "Passing": [ ... ],
                "Shot Defense": [ ... ],
            },
        }

    Empty families render as empty lists rather than missing keys so the
    frontend always has the same shape to iterate.
    """
    season_type = "Playoffs" if is_playoff else "Regular Season"
    rows = _query_rows(db, player_id, season, season_type)

    if not rows:
        try:
            sync_player_tracking_stats(
                db, season=season, player_ids=[player_id], season_type=season_type
            )
            rows = _query_rows(db, player_id, season, season_type)
        except LiveFetchBlockedError:
            rows = []
        except Exception as exc:  # noqa: BLE001 — keep the user-facing read graceful
            logger.warning(
                "On-demand player tracking sync failed for %s/%s: %s",
                player_id,
                season,
                exc,
            )
            rows = []

    families: Dict[str, List[Dict[str, Any]]] = {label: [] for label in PUBLIC_FAMILY_ORDER}
    for row in rows:
        public_label = _FAMILY_LABEL_BY_RAW.get(row.tracking_family, row.tracking_family)
        families.setdefault(public_label, []).append(_row_to_dict(row))

    return {
        "player_id": player_id,
        "season": season,
        "is_playoff": is_playoff,
        "families": families,
    }
