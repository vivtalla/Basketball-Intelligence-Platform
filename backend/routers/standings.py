from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Team, TeamStanding
from models.standings import StandingsEntry
from services.standings_service import compute_standings_data

router = APIRouter()


def _standings_from_db(season: str, db: Session) -> Optional[List[StandingsEntry]]:
    """Return materialized standings from team_standings table, or None if empty."""
    rows = (
        db.query(TeamStanding, Team)
        .join(Team, Team.id == TeamStanding.team_id)
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


@router.get("", response_model=List[StandingsEntry])
def get_standings(
    season: str = Query("2024-25"),
    db: Session = Depends(get_db),
):
    """Return league standings.

    Reads from the materialized team_standings table when available.
    Falls back to live computation from player_game_logs if the table is empty
    (e.g. first run before materialize_standings has been called).
    """
    entries = _standings_from_db(season, db)
    if entries is None:
        # Fallback: compute on-the-fly from player_game_logs
        raw = compute_standings_data(season, db)
        from models.standings import StandingsEntry as SE
        entries = [SE(**{
            "team_id": d["team_id"],
            "team_city": d["team_city"],
            "team_name": d["team_name"],
            "conference": d["conference"],
            "division": d["division"],
            "playoff_rank": d["playoff_rank"],
            "wins": d["wins"],
            "losses": d["losses"],
            "win_pct": d["win_pct"],
            "games_back": d["games_back"],
            "l10": d["l10"],
            "home_record": d["home_record"],
            "road_record": d["road_record"],
            "pts_pg": None,
            "opp_pts_pg": None,
            "diff_pts_pg": None,
            "current_streak": d["current_streak_str"],
            "clinch_indicator": None,
            "abbreviation": d["abbreviation"],
        }) for d in raw]

    entries.sort(key=lambda e: (e.conference, e.playoff_rank))
    return entries
