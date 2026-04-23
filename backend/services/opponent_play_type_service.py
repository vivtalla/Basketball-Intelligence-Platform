from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy.orm import Session

from data.nba_client import get_synergy_team_play_types
from db.models import Team
from models.decision import OpponentPlayTypeResponse, OpponentPlayTypeRow


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_opponent_play_type_report(
    db: Session,
    team_abbr: str,
    season: str,
) -> OpponentPlayTypeResponse:
    """Build opponent play-type tendencies report from Synergy data."""
    try:
        team = db.query(Team).filter(Team.abbreviation == team_abbr).first()
        if not team:
            return OpponentPlayTypeResponse(
                team_abbr=team_abbr, season=season, plays=[], data_status="unavailable"
            )

        rows = get_synergy_team_play_types(season, type_grouping="offensive")
        if not rows:
            return OpponentPlayTypeResponse(
                team_abbr=team_abbr, season=season, plays=[], data_status="unavailable"
            )

        plays: List[OpponentPlayTypeRow] = [
            OpponentPlayTypeRow(
                play_type=row.get("PLAY_TYPE", "Unknown"),
                poss_pct=_as_float(row.get("POSS_PCT")),
                ppp=_as_float(row.get("PPP")),
                percentile=_as_float(row.get("PERCENTILE")),
                fg_pct=_as_float(row.get("FG_PCT")),
                score_pct=_as_float(row.get("SCORE_PCT")),
            )
            for row in rows
            if row.get("TEAM_ABBREVIATION") == team_abbr
        ]

        plays.sort(key=lambda p: p.poss_pct or 0, reverse=True)

        return OpponentPlayTypeResponse(
            team_abbr=team_abbr,
            season=season,
            plays=plays,
            data_status="ready" if plays else "unavailable",
        )

    except Exception:
        return OpponentPlayTypeResponse(
            team_abbr=team_abbr, season=season, plays=[], data_status="unavailable"
        )
