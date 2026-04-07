from __future__ import annotations

from sqlalchemy.orm import Session

from services.decision_support_service import build_matchup_flags_report as _build_matchup_flags_report


def build_matchup_flag_report(
    db: Session,
    team_abbr: str,
    opponent_abbr: str,
    season: str,
    window_games: int = 10,
):
    del window_games
    return _build_matchup_flags_report(
        db=db,
        team_abbr=team_abbr,
        opponent_abbr=opponent_abbr,
        season=season,
    ).model_dump()
