"""Game log endpoints — per-game stats for a player in a season."""

import datetime
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from data.nba_client import _active_nba_season
from db.database import get_db
from db.models import PlayerGameLog
from models.stats import GameLogEntry, GameLogResponse, GameLogSeasonAverages

router = APIRouter()

_CURRENT_SEASON_STALE_SECONDS = 24 * 3600  # re-fetch current season after 24 h


def _is_stale(row: PlayerGameLog, season: str) -> bool:
    """Return True if the cached row should be refreshed."""
    if row.synced_at is None:
        return True
    if season != _active_nba_season():
        return False  # historical seasons never stale
    age = (datetime.datetime.utcnow() - row.synced_at).total_seconds()
    return age > _CURRENT_SEASON_STALE_SECONDS


def _load_from_db(
    db: Session, player_id: int, season: str, season_type: str
) -> Tuple[List[dict], str, Optional[str]]:
    """Return cached game logs from PostgreSQL with readiness metadata."""
    rows = db.execute(
        select(PlayerGameLog)
        .where(
            PlayerGameLog.player_id == player_id,
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == season_type,
        )
        .order_by(PlayerGameLog.game_date.desc())
    ).scalars().all()

    if not rows:
        return [], "missing", None

    data_status = "stale" if any(_is_stale(r, season) for r in rows) else "ready"
    latest_synced = max(
        (row.synced_at for row in rows if row.synced_at is not None),
        default=None,
    )
    return (
        [_row_to_dict(r) for r in rows],
        data_status,
        latest_synced.isoformat() if latest_synced else None,
    )


def _row_to_dict(r: PlayerGameLog) -> dict:
    return {
        "game_id": r.game_id,
        "game_date": r.game_date.isoformat() if r.game_date else None,
        "matchup": r.matchup,
        "wl": r.wl,
        "min": r.min,
        "pts": r.pts,
        "reb": r.reb,
        "ast": r.ast,
        "stl": r.stl,
        "blk": r.blk,
        "tov": r.tov,
        "fgm": r.fgm,
        "fga": r.fga,
        "fg_pct": r.fg_pct,
        "fg3m": r.fg3m,
        "fg3a": r.fg3a,
        "fg3_pct": r.fg3_pct,
        "ftm": r.ftm,
        "fta": r.fta,
        "ft_pct": r.ft_pct,
        "oreb": r.oreb,
        "dreb": r.dreb,
        "pf": r.pf,
        "plus_minus": r.plus_minus,
    }


@router.get("/{player_id}", response_model=GameLogResponse)
def player_game_logs(
    player_id: int,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    db: Session = Depends(get_db),
):
    """Return per-game stats for a player, ordered newest-first.

    Reads only from PostgreSQL. Current-season rows can be marked stale based on
    `synced_at`, but the route never falls back to a remote fetch.

    season_type: 'Regular Season' | 'Playoffs' | 'Pre Season'
    """
    logs, data_status, last_synced_at = _load_from_db(db, player_id, season, season_type)

    if not logs:
        return GameLogResponse(
            player_id=player_id,
            season=season,
            season_type=season_type,
            games=[],
            season_averages=GameLogSeasonAverages(),
            gp=0,
            data_status=data_status,
            last_synced_at=last_synced_at,
        )

    # Compute rolling 5-game averages for pts/reb/ast (newest-first order)
    def _rolling_avg(values: List[Optional[int]], window: int = 5) -> List[Optional[float]]:
        result = []
        for i in range(len(values)):
            end = min(i + window, len(values))
            chunk = [v for v in values[i:end] if v is not None]
            result.append(round(sum(chunk) / len(chunk), 1) if chunk else None)
        return result

    pts_vals = [g["pts"] for g in logs]
    reb_vals = [g["reb"] for g in logs]
    ast_vals = [g["ast"] for g in logs]

    pts_roll = _rolling_avg(pts_vals)
    reb_roll = _rolling_avg(reb_vals)
    ast_roll = _rolling_avg(ast_vals)

    for i, game in enumerate(logs):
        game["pts_roll5"] = pts_roll[i]
        game["reb_roll5"] = reb_roll[i]
        game["ast_roll5"] = ast_roll[i]

    def _avg(vals: List[Optional[float]]) -> Optional[float]:
        clean = [v for v in vals if v is not None]
        return round(sum(clean) / len(clean), 1) if clean else None

    season_avgs = {
        "pts": _avg(pts_vals),
        "reb": _avg(reb_vals),
        "ast": _avg(ast_vals),
        "stl": _avg([g["stl"] for g in logs]),
        "blk": _avg([g["blk"] for g in logs]),
        "tov": _avg([g["tov"] for g in logs]),
        "fg_pct": _avg([g["fg_pct"] for g in logs if g["fg_pct"] is not None]),
        "fg3_pct": _avg([g["fg3_pct"] for g in logs if g["fg3_pct"] is not None]),
        "ft_pct": _avg([g["ft_pct"] for g in logs if g["ft_pct"] is not None]),
        "min": _avg([g["min"] for g in logs]),
        "plus_minus": _avg([g["plus_minus"] for g in logs]),
    }

    return GameLogResponse(
        player_id=player_id,
        season=season,
        season_type=season_type,
        games=[GameLogEntry(**game) for game in logs],
        season_averages=GameLogSeasonAverages(**season_avgs),
        gp=len(logs),
        data_status=data_status,
        last_synced_at=last_synced_at,
    )
