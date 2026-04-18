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
from services.gravity_service import build_gravity_profile
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

GRAVITY_SORTABLE_STATS = {
    "overall_gravity",
    "shooting_gravity",
    "rim_gravity",
    "creation_gravity",
    "roll_or_screen_gravity",
    "off_ball_gravity",
    "spacing_lift",
}

LEADERBOARD_METRIC_FIELDS = tuple(sorted(SORTABLE_STATS | GRAVITY_SORTABLE_STATS))

# Pct fields that can be derived from raw counts when the stored column is NULL.
_DERIVED_PCTS = {
    "fg_pct":  ("fgm",  "fga",  None),
    "fg3_pct": ("fg3m", "fg3a", None),
    "ft_pct":  ("ftm",  "fta",  None),
    # efg = (fgm + 0.5 * fg3m) / fga  — handled separately
}


def _metric_value(stat_row: "SeasonStat", key: str) -> Optional[float]:  # type: ignore[name-defined]
    value = getattr(stat_row, key, None)
    if value is not None:
        return float(value)
    # Derive shooting pcts from raw counts when the stored column is NULL
    if key in _DERIVED_PCTS:
        made_attr, att_attr, _ = _DERIVED_PCTS[key]
        att = getattr(stat_row, att_attr, None) or 0
        if not att:
            return None
        made = getattr(stat_row, made_attr, None) or 0
        return round(made / att, 3)
    if key == "efg_pct":
        fga = getattr(stat_row, "fga", None) or 0
        if not fga:
            return None
        fgm = getattr(stat_row, "fgm", None) or 0
        fg3m = getattr(stat_row, "fg3m", None) or 0
        return round((fgm + 0.5 * fg3m) / fga, 3)
    if key == "ts_pct":
        # TS% = PTS / (2 * (FGA + 0.44 * FTA))
        pts = getattr(stat_row, "pts", None) or 0
        fga = getattr(stat_row, "fga", None) or 0
        fta = getattr(stat_row, "fta", None) or 0
        denom = 2 * (fga + 0.44 * fta)
        return round(pts / denom, 3) if denom else None
    return None


def _gravity_metric_values(db: Session, player_id: int, season: str, season_type: str) -> dict:
    profile = build_gravity_profile(db, player_id=player_id, season=season, season_type=season_type)
    return {
        "overall_gravity": profile.overall_gravity,
        "shooting_gravity": profile.shooting_gravity,
        "rim_gravity": profile.rim_gravity,
        "creation_gravity": profile.creation_gravity,
        "roll_or_screen_gravity": profile.roll_or_screen_gravity,
        "off_ball_gravity": profile.off_ball_gravity,
        "spacing_lift": profile.spacing_lift,
    }


def _entry_metric_values(db: Session, stat_row: SeasonStat, player_id: int, season_type: str) -> dict:
    values = {
        key: _metric_value(stat_row, key)
        for key in SORTABLE_STATS
    }
    if stat_row.season and season_type == "Regular Season":
        values.update(_gravity_metric_values(db, player_id, stat_row.season, season_type))
    else:
        values.update({key: None for key in GRAVITY_SORTABLE_STATS})
    return values


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
    if stat not in SORTABLE_STATS and stat not in GRAVITY_SORTABLE_STATS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stat '{stat}'. Must be one of: {sorted(SORTABLE_STATS | GRAVITY_SORTABLE_STATS)}",
        )

    is_playoff = season_type == "Playoffs"
    stat_col = getattr(SeasonStat, stat, None)

    q = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == is_playoff,  # noqa: E712
            SeasonStat.gp >= min_gp,
        )
    )
    if stat_col is not None:
        q = q.filter(stat_col.isnot(None))
    if team:
        q = q.filter(SeasonStat.team_abbreviation == team)

    # Fetch extra rows to account for mid-season trades (one DB row per team).
    # Sort by stat desc then gp desc so the best/most-played row comes first per player.
    if stat_col is not None:
        raw = q.order_by(stat_col.desc(), SeasonStat.gp.desc()).limit(limit * 4).all()
    else:
        raw = q.order_by(SeasonStat.gp.desc(), SeasonStat.min_total.desc()).limit(max(limit * 8, 200)).all()

    # Deduplicate: keep the first (highest-stat) row per player_id
    seen_ids: set = set()
    rows = []
    for stat_row, player in raw:
        if player.id not in seen_ids:
            seen_ids.add(player.id)
            rows.append((stat_row, player))
        if stat not in GRAVITY_SORTABLE_STATS and len(rows) >= limit:
            break

    if stat in GRAVITY_SORTABLE_STATS:
        gravity_rows = []
        for stat_row, player in rows:
            metric_values = _entry_metric_values(db, stat_row, player.id, season_type)
            value = metric_values.get(stat)
            if value is not None:
                gravity_rows.append((float(value), metric_values, stat_row, player))
        gravity_rows.sort(key=lambda item: item[0], reverse=True)
        rows_with_metrics = gravity_rows[:limit]
    else:
        rows_with_metrics = [
            (float(getattr(stat_row, stat)), _entry_metric_values(db, stat_row, player.id, season_type), stat_row, player)
            for stat_row, player in rows
        ]

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
            stat_value=stat_value,
            pts_pg=stat_row.pts_pg,
            reb_pg=stat_row.reb_pg,
            ast_pg=stat_row.ast_pg,
            ts_pct=stat_row.ts_pct,
            per=stat_row.per,
            bpm=stat_row.bpm,
            metric_values=metric_values,
        )
        for rank, (stat_value, metric_values, stat_row, player) in enumerate(rows_with_metrics, start=1)
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
