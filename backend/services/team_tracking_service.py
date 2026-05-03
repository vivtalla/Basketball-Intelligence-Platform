"""Sprint 86 Stream C — Team tracking dashboard service.

Reads :class:`TeamTrackingStat` rows for a single team and groups them into
the same three families used by :mod:`services.player_tracking_service`:

- ``Shot Creation`` — touches, drives, paint/close touches, pull-up production
- ``Passing``       — passes made / received
- ``Shot Defense``  — close-defense distance bucket FGA / FG%

If no rows are persisted for the requested season + season type, the service
calls :func:`sync_team_tracking_stats` to fetch + persist on the fly. Any
``LiveFetchBlockedError`` (user-facing read with cache miss) is swallowed and
the empty payload is returned so the frontend can render a "no data" state.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from data.nba_client import LiveFetchBlockedError
from db.models import TeamTrackingStat
from services.gravity_sync_service import sync_team_tracking_stats


logger = logging.getLogger(__name__)


_FAMILY_LABEL_BY_RAW: Dict[str, str] = {
    "shots": "Shot Creation",
    "passing": "Passing",
    "shot_defense": "Shot Defense",
}

PUBLIC_FAMILY_ORDER: List[str] = ["Shot Creation", "Passing", "Shot Defense"]


def _row_to_dict(row: TeamTrackingStat) -> Dict[str, Any]:
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
    db: Session, team_id: int, season: str, season_type: str
) -> List[TeamTrackingStat]:
    return (
        db.query(TeamTrackingStat)
        .filter(
            TeamTrackingStat.team_id == team_id,
            TeamTrackingStat.season == season,
            TeamTrackingStat.season_type == season_type,
        )
        .order_by(TeamTrackingStat.tracking_family, TeamTrackingStat.split_key)
        .all()
    )


def get_team_tracking(
    db: Session,
    team_id: int,
    season: str,
    is_playoff: bool = False,
) -> Dict[str, Any]:
    """Return one team's tracking dashboard grouped by public family label.

    Response shape::

        {
            "team_id": int,
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
    rows = _query_rows(db, team_id, season, season_type)

    if not rows:
        try:
            sync_team_tracking_stats(
                db, season=season, season_type=season_type, team_ids=[team_id]
            )
            rows = _query_rows(db, team_id, season, season_type)
        except LiveFetchBlockedError:
            rows = []
        except Exception as exc:  # noqa: BLE001 — keep the user-facing read graceful
            logger.warning(
                "On-demand team tracking sync failed for %s/%s: %s",
                team_id,
                season,
                exc,
            )
            rows = []

    families: Dict[str, List[Dict[str, Any]]] = {label: [] for label in PUBLIC_FAMILY_ORDER}
    for row in rows:
        public_label = _FAMILY_LABEL_BY_RAW.get(row.tracking_family, row.tracking_family)
        families.setdefault(public_label, []).append(_row_to_dict(row))

    return {
        "team_id": team_id,
        "season": season,
        "is_playoff": is_playoff,
        "families": families,
    }
