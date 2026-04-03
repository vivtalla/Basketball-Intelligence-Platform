from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Team, TeamStanding
from models.standings import StandingsEntry, StandingsHistoryResponse
from services.standings_service import get_standings_history

router = APIRouter()


def _standings_from_db(season: str, db: Session) -> Optional[List[StandingsEntry]]:
    """Return materialized standings from team_standings table, or None if empty.

    Uses the most recent snapshot per team so the table's daily history rows
    don't produce duplicate entries.
    """
    # Subquery: latest snapshot_date per team for this season
    latest_sq = (
        db.query(
            TeamStanding.team_id,
            func.max(TeamStanding.snapshot_date).label("latest_date"),
        )
        .filter(TeamStanding.season == season)
        .group_by(TeamStanding.team_id)
        .subquery()
    )

    rows = (
        db.query(TeamStanding, Team)
        .join(Team, Team.id == TeamStanding.team_id)
        .join(
            latest_sq,
            (TeamStanding.team_id == latest_sq.c.team_id)
            & (TeamStanding.snapshot_date == latest_sq.c.latest_date),
        )
        .filter(TeamStanding.season == season)
        .all()
    )
    if not rows:
        return None

    # Rebuild the full StandingsEntry shape from the materialized table.
    entries: List[dict] = []
    for standing, team in rows:
        streak_str = ""
        if standing.streak_type:
            streak_count = abs(standing.current_streak or 0)
            streak_str = f"{standing.streak_type}{streak_count}"

        wins = standing.wins or 0
        losses = standing.losses or 0
        gp = wins + losses

        entries.append({
            "team_id": team.id,
            "team_city": team.city or "",
            "team_name": team.name or "",
            "conference": standing.conference or "",
            "division": standing.division or "",
            "playoff_rank": 0,
            "wins": wins,
            "losses": losses,
            "win_pct": wins / gp if gp > 0 else 0.0,
            "games_back": None,
            "l10": f"{standing.last_10_wins or 0}-{standing.last_10_losses or 0}",
            "home_record": f"{standing.home_wins or 0}-{standing.home_losses or 0}",
            "road_record": f"{standing.road_wins or 0}-{standing.road_losses or 0}",
            "pts_pg": None,
            "opp_pts_pg": None,
            "diff_pts_pg": None,
            "current_streak": streak_str,
            "clinch_indicator": None,
            "abbreviation": team.abbreviation,
        })

    # Assign playoff_rank and games_back within each conference
    for conf in ("East", "West"):
        conf_entries = [e for e in entries if e["conference"] == conf]
        conf_entries.sort(key=lambda e: (-e["wins"], e["losses"]))
        if not conf_entries:
            continue
        leader_w = conf_entries[0]["wins"]
        leader_l = conf_entries[0]["losses"]
        for rank, e in enumerate(conf_entries, start=1):
            e["playoff_rank"] = rank
            e["games_back"] = 0.0 if rank == 1 else ((leader_w - e["wins"]) + (e["losses"] - leader_l)) / 2.0

    return [StandingsEntry(**e) for e in entries]


@router.get("/history", response_model=List[StandingsHistoryResponse])
def get_standings_history_endpoint(
    season: str = Query("2024-25"),
    days: int = Query(30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Return per-team win-pct time series for the last N days."""
    return get_standings_history(season, days, db)


@router.get("", response_model=List[StandingsEntry])
def get_standings(
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return league standings.

    Reads only from the materialized team_standings table.
    """
    entries = _standings_from_db(season, db)
    if entries is None:
        return []

    entries.sort(key=lambda e: (e.conference, e.playoff_rank))
    return entries
