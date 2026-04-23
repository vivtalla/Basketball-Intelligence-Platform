from __future__ import annotations

from sqlalchemy.orm import Session

from data.nba_client import get_team_clutch_stats
from db.models import Team
from models.team import TeamClutchResponse


def build_team_clutch_analytics(
    db: Session,
    team_abbr: str,
    season: str,
) -> TeamClutchResponse:
    """Build team clutch analytics (last 5 min, score within 5)."""
    try:
        team = db.query(Team).filter(Team.abbreviation == team_abbr).first()

        if not team:
            return TeamClutchResponse(
                team_abbr=team_abbr,
                season=season,
                data_status="unavailable",
            )

        rows = get_team_clutch_stats(season)

        if not rows:
            return TeamClutchResponse(
                team_abbr=team_abbr,
                season=season,
                data_status="unavailable",
            )

        team_row = next((r for r in rows if r.get("TEAM_ABBREVIATION") == team_abbr), None)

        if not team_row:
            return TeamClutchResponse(
                team_abbr=team_abbr,
                season=season,
                data_status="unavailable",
            )

        gp = team_row.get("GP")
        w = team_row.get("W")
        l = team_row.get("L")
        w_pct = team_row.get("W_PCT")
        pts_pg = team_row.get("PTS")
        plus_minus_pg = team_row.get("PLUS_MINUS")
        fg_pct = team_row.get("FG_PCT")
        ft_pct = team_row.get("FT_PCT")
        w_pct_rank = team_row.get("W_PCT_RANK")
        plus_minus_rank = team_row.get("PLUS_MINUS_RANK")

        ts_pct = None
        fga = team_row.get("FGA")
        fta = team_row.get("FTA")
        pts = team_row.get("PTS")
        if fga and fta and pts:
            ts_pct = pts / (2 * (fga + 0.44 * fta)) if (fga + 0.44 * fta) > 0 else None
            if ts_pct:
                ts_pct = round(ts_pct, 3)

        return TeamClutchResponse(
            team_abbr=team_abbr,
            season=season,
            gp=gp,
            w=w,
            l=l,
            w_pct=w_pct,
            pts_pg=pts_pg,
            plus_minus_pg=plus_minus_pg,
            fg_pct=fg_pct,
            ft_pct=ft_pct,
            ts_pct=ts_pct,
            w_pct_rank=w_pct_rank,
            plus_minus_rank=plus_minus_rank,
            data_status="ready",
        )

    except Exception:
        return TeamClutchResponse(
            team_abbr=team_abbr,
            season=season,
            data_status="error",
        )
