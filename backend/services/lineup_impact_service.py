from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from services.decision_support_service import build_lineup_impact_report as _build_lineup_impact_report


def build_lineup_impact_report(
    db: Session,
    team_abbr: str,
    season: str,
    opponent_abbr: Optional[str] = None,
    window_games: int = 10,
    min_possessions: int = 25,
):
    return _build_lineup_impact_report(
        db=db,
        team_abbr=team_abbr,
        season=season,
        opponent_abbr=opponent_abbr,
        window_games=window_games,
        min_possessions=min_possessions,
    ).model_dump()
