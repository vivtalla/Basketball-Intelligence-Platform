"""Sprint 78 (Team CF1): Shareable story-card endpoints.

Server-rendered Open Graph (OG) images for the broadsheet share surface.
Each route returns a 1200x630 PNG with the broadsheet visual language so
that links shared on X / Instagram / Slack render with a CourtVue card
preview.

Public routes:

- ``GET /api/share/player/{player_id}.png?season=YYYY-YY``
- ``GET /api/share/game/{game_id}.png``
- ``GET /api/share/series/{series_id}.png``
- ``GET /api/share/milestone/{player_id}/{milestone_key}.png``

Each response sets ``Cache-Control: public, max-age=3600`` (1 hour) — the
underlying data only changes nightly and we want OG crawlers to re-pull
on a cadence the user can feel.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from services.share_card_service import (
    render_game_card,
    render_milestone_card,
    render_player_card,
    render_series_card,
)

router = APIRouter()

_CACHE_HEADER = "public, max-age=3600"


def _png_response(content: bytes) -> Response:
    return Response(
        content=content,
        media_type="image/png",
        headers={"Cache-Control": _CACHE_HEADER},
    )


@router.get("/player/{player_id}.png")
def share_player_card(
    player_id: int,
    season: Optional[str] = Query(None, description="Season string e.g. '2024-25'"),
    db: Session = Depends(get_db),
) -> Response:
    """Render a player season share card. Falls back to the active season
    when none is supplied."""
    season_key = season or _active_nba_season()
    png = render_player_card(db, player_id, season_key)
    return _png_response(png)


@router.get("/game/{game_id}.png")
def share_game_card(
    game_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Render a game-recap share card."""
    png = render_game_card(db, game_id)
    return _png_response(png)


@router.get("/series/{series_id}.png")
def share_series_card(
    series_id: str,
    db: Session = Depends(get_db),
) -> Response:
    """Render a playoff-series share card."""
    png = render_series_card(db, series_id)
    return _png_response(png)


@router.get("/milestone/{player_id}/{milestone_key}.png")
def share_milestone_card(
    player_id: int,
    milestone_key: str,
    db: Session = Depends(get_db),
) -> Response:
    """Render a milestone share card. CF5 owns the milestone schema; this
    endpoint returns a broadsheet placeholder until those tables land."""
    png = render_milestone_card(db, player_id, milestone_key)
    return _png_response(png)
