from __future__ import annotations

from sqlalchemy.orm import Session

from db.models import Team
from models.team import TeamPeriodScoringResponse


def build_team_period_scoring(
    db: Session,
    team_abbr: str,
    season: str,
) -> TeamPeriodScoringResponse:
    """Build team period/half scoring profile. Currently returns unavailable as nba_api does not provide period breakdown."""
    return TeamPeriodScoringResponse(
        team_abbr=team_abbr,
        season=season,
        by_period=[],
        by_half=[],
        best_period=None,
        worst_period=None,
        data_status="unavailable",
    )
