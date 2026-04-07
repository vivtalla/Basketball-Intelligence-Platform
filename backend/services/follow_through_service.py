from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

from sqlalchemy.orm import Session

from models.decision import FollowThroughRequest
from services.decision_support_service import build_follow_through_report as _build_follow_through_report


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
    response = _build_follow_through_report(
        db=db,
        payload=FollowThroughRequest(
            source_type=source_type,
            source_id=source_id,
            team=team_abbreviation,
            opponent=opponent_abbreviation,
            player_ids=list(player_ids or []),
            lineup_key=lineup_key,
            season=season,
            window=window_games,
            context={key: str(value) for key, value in (context or {}).items()},
        ),
    )
    return response.model_dump()
