from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, SeasonStat
from models.leaderboard import LeaderboardEntry, LeaderboardResponse

router = APIRouter()

SORTABLE_STATS = {
    "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg", "tov_pg",
    "fg_pct", "fg3_pct", "ft_pct", "min_pg",
    "ts_pct", "efg_pct", "usg_pct", "per", "bpm", "ws", "vorp",
    "off_rating", "def_rating", "net_rating", "pie", "darko",
    "obpm", "dbpm", "ftr", "par3", "ast_tov", "oreb_pct",
    "epm", "rapm", "lebron", "raptor", "pipm",
}


@router.get("/seasons")
def available_seasons(db: Session = Depends(get_db)) -> List[str]:
    """Return distinct seasons available in the database, newest first."""
    rows = (
        db.query(SeasonStat.season)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .distinct()
        .order_by(SeasonStat.season.desc())
        .all()
    )
    return [r.season for r in rows]


@router.get("", response_model=LeaderboardResponse)
def leaderboard(
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    stat: str = Query("pts_pg", description="Stat column to rank by"),
    season_type: str = Query("Regular Season"),
    limit: int = Query(25, ge=1, le=100),
    min_gp: int = Query(15, ge=1),
    db: Session = Depends(get_db),
):
    if stat not in SORTABLE_STATS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stat '{stat}'. Must be one of: {sorted(SORTABLE_STATS)}",
        )

    is_playoff = season_type == "Playoffs"
    stat_col = getattr(SeasonStat, stat)

    rows = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == is_playoff,  # noqa: E712
            SeasonStat.gp >= min_gp,
            stat_col.isnot(None),
        )
        .order_by(stat_col.desc())
        .limit(limit)
        .all()
    )

    entries = [
        LeaderboardEntry(
            rank=rank,
            player_id=player.id,
            player_name=player.full_name,
            team_abbreviation=stat_row.team_abbreviation,
            headshot_url=player.headshot_url or "",
            gp=stat_row.gp or 0,
            stat_value=float(getattr(stat_row, stat)),
        )
        for rank, (stat_row, player) in enumerate(rows, start=1)
    ]

    return LeaderboardResponse(
        stat=stat,
        season=season,
        season_type=season_type,
        entries=entries,
    )
