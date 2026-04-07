from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, SeasonStat
from models.leaderboard import (
    CareerLeaderboardEntry,
    CareerLeaderboardResponse,
    CustomMetricRequest,
    CustomMetricResponse,
    LeaderboardEntry,
    LeaderboardResponse,
)
from services.custom_metric_service import build_custom_metric_report
from services.sync_service import canonical_player_name

router = APIRouter()

SORTABLE_STATS = {
    "pts", "reb", "ast", "stl", "blk", "tov",
    "fgm", "fga", "fg3m", "fg3a", "ftm", "fta",
    "oreb", "dreb", "pf", "min_total",
    "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg", "tov_pg",
    "fg_pct", "fg3_pct", "ft_pct", "min_pg",
    "ts_pct", "efg_pct", "usg_pct", "per", "bpm", "ws", "vorp",
    "off_rating", "def_rating", "net_rating", "pie", "darko",
    "obpm", "dbpm", "ftr", "par3", "ast_tov", "oreb_pct",
    "epm", "rapm", "lebron", "raptor", "pipm",
}

LEADERBOARD_METRIC_FIELDS = tuple(sorted(SORTABLE_STATS))

CAREER_SORTABLE_STATS = {
    "pts_pg", "reb_pg", "ast_pg", "stl_pg", "blk_pg",
    "bpm", "ws", "vorp", "per", "ts_pct",
}


@router.post("/custom-metric", response_model=CustomMetricResponse)
def custom_metric(
    payload: CustomMetricRequest,
    db: Session = Depends(get_db),
):
    return build_custom_metric_report(db, payload)


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


@router.get("/teams")
def available_teams(
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    db: Session = Depends(get_db),
) -> List[str]:
    """Return distinct team abbreviations for a season, sorted alphabetically."""
    rows = (
        db.query(SeasonStat.team_abbreviation)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .distinct()
        .order_by(SeasonStat.team_abbreviation)
        .all()
    )
    return [r.team_abbreviation for r in rows]


@router.get("", response_model=LeaderboardResponse)
def leaderboard(
    season: str = Query(..., description='Season ID, e.g. "2023-24"'),
    stat: str = Query("pts_pg", description="Stat column to rank by"),
    season_type: str = Query("Regular Season"),
    limit: int = Query(25, ge=1, le=100),
    min_gp: int = Query(15, ge=1),
    team: Optional[str] = Query(None, description="Filter by team abbreviation"),
    db: Session = Depends(get_db),
):
    if stat not in SORTABLE_STATS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stat '{stat}'. Must be one of: {sorted(SORTABLE_STATS)}",
        )

    is_playoff = season_type == "Playoffs"
    stat_col = getattr(SeasonStat, stat)

    q = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == is_playoff,  # noqa: E712
            SeasonStat.gp >= min_gp,
            stat_col.isnot(None),
        )
    )
    if team:
        q = q.filter(SeasonStat.team_abbreviation == team)

    # Fetch extra rows to account for mid-season trades (one DB row per team).
    # Sort by stat desc then gp desc so the best/most-played row comes first per player.
    raw = q.order_by(stat_col.desc(), SeasonStat.gp.desc()).limit(limit * 4).all()

    # Deduplicate: keep the first (highest-stat) row per player_id
    seen_ids: set = set()
    rows = []
    for stat_row, player in raw:
        if player.id not in seen_ids:
            seen_ids.add(player.id)
            rows.append((stat_row, player))
        if len(rows) >= limit:
            break

    entries = [
        LeaderboardEntry(
            rank=rank,
            player_id=player.id,
            player_name=canonical_player_name(
                player.full_name,
                player.first_name or "",
                player.last_name or "",
            ),
            team_abbreviation=stat_row.team_abbreviation,
            headshot_url=player.headshot_url or "",
            gp=stat_row.gp or 0,
            stat_value=float(getattr(stat_row, stat)),
            pts_pg=stat_row.pts_pg,
            reb_pg=stat_row.reb_pg,
            ast_pg=stat_row.ast_pg,
            ts_pct=stat_row.ts_pct,
            per=stat_row.per,
            bpm=stat_row.bpm,
            metric_values={
                key: (float(value) if value is not None else None)
                for key in LEADERBOARD_METRIC_FIELDS
                for value in [getattr(stat_row, key, None)]
            },
        )
        for rank, (stat_row, player) in enumerate(rows, start=1)
    ]

    return LeaderboardResponse(
        stat=stat,
        season=season,
        season_type=season_type,
        entries=entries,
    )


@router.get("/career", response_model=CareerLeaderboardResponse)
def career_leaderboard(
    stat: str = Query("pts_pg", description="Career stat to rank by"),
    min_gp: int = Query(15, ge=1, description="Minimum games per season to include a season row"),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if stat not in CAREER_SORTABLE_STATS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid career stat '{stat}'. Must be one of: {sorted(CAREER_SORTABLE_STATS)}",
        )

    stat_col = getattr(SeasonStat, stat)

    # Aggregate across all regular-season rows per player
    agg = (
        db.query(
            Player,
            func.count(SeasonStat.id).label("seasons_played"),
            func.sum(SeasonStat.gp).label("career_gp"),
            func.avg(stat_col).label("stat_avg"),
        )
        .join(SeasonStat, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= min_gp,
            stat_col.isnot(None),
        )
        .group_by(Player.id)
        .order_by(func.avg(stat_col).desc())
        .limit(limit)
        .all()
    )

    entries = [
        CareerLeaderboardEntry(
            rank=rank,
            player_id=player.id,
            player_name=canonical_player_name(
                player.full_name,
                player.first_name or "",
                player.last_name or "",
            ),
            headshot_url=player.headshot_url or "",
            seasons_played=int(seasons_played),
            career_gp=int(career_gp) if career_gp else 0,
            stat_value=float(stat_avg),
        )
        for rank, (player, seasons_played, career_gp, stat_avg) in enumerate(agg, start=1)
    ]

    return CareerLeaderboardResponse(stat=stat, entries=entries)
