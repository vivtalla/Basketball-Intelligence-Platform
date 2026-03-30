"""Game log endpoints — per-game stats for a player in a season."""

import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from data.nba_client import get_player_game_logs, _active_nba_season, _cache_ttl_for_season
from db.database import get_db
from db.models import PlayerGameLog

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
) -> Optional[List[dict]]:
    """Return cached game logs from PostgreSQL, or None if missing/stale."""
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
        return None

    # If any row is stale, refresh the whole batch
    if any(_is_stale(r, season) for r in rows):
        return None

    return [_row_to_dict(r) for r in rows]


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


def _upsert_logs(
    db: Session,
    player_id: int,
    season: str,
    season_type: str,
    logs: List[dict],
) -> None:
    """Write fresh logs to player_game_logs, replacing any existing rows."""
    db.execute(
        PlayerGameLog.__table__.delete().where(
            PlayerGameLog.player_id == player_id,
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == season_type,
        )
    )
    now = datetime.datetime.utcnow()
    for g in logs:
        raw_date = g.get("game_date")
        if raw_date:
            try:
                game_date = datetime.datetime.strptime(raw_date, "%b %d, %Y").date()
            except ValueError:
                try:
                    game_date = datetime.date.fromisoformat(raw_date)
                except ValueError:
                    game_date = None
        else:
            game_date = None

        db.add(PlayerGameLog(
            player_id=player_id,
            game_id=g.get("game_id", ""),
            season=season,
            season_type=season_type,
            game_date=game_date,
            matchup=g.get("matchup"),
            wl=g.get("wl"),
            min=g.get("min"),
            pts=g.get("pts"),
            reb=g.get("reb"),
            ast=g.get("ast"),
            stl=g.get("stl"),
            blk=g.get("blk"),
            tov=g.get("tov"),
            fgm=g.get("fgm"),
            fga=g.get("fga"),
            fg_pct=g.get("fg_pct"),
            fg3m=g.get("fg3m"),
            fg3a=g.get("fg3a"),
            fg3_pct=g.get("fg3_pct"),
            ftm=g.get("ftm"),
            fta=g.get("fta"),
            ft_pct=g.get("ft_pct"),
            oreb=g.get("oreb"),
            dreb=g.get("dreb"),
            pf=g.get("pf"),
            plus_minus=g.get("plus_minus"),
            synced_at=now,
        ))
    db.commit()


@router.get("/{player_id}")
def player_game_logs(
    player_id: int,
    season: str = "2024-25",
    season_type: str = "Regular Season",
    db: Session = Depends(get_db),
):
    """Return per-game stats for a player, ordered newest-first.

    Serves from PostgreSQL when available; falls back to NBA API and persists
    results. Current season refreshes after 24 h; historical seasons never re-fetch.

    season_type: 'Regular Season' | 'Playoffs' | 'Pre Season'
    """
    logs = _load_from_db(db, player_id, season, season_type)

    if logs is None:
        try:
            logs = get_player_game_logs(player_id, season, season_type)
        except Exception:
            logs = []

        if logs:
            _upsert_logs(db, player_id, season, season_type, logs)

    if not logs:
        return {
            "player_id": player_id,
            "season": season,
            "season_type": season_type,
            "games": [],
            "season_averages": {},
            "gp": 0,
        }

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

    return {
        "player_id": player_id,
        "season": season,
        "season_type": season_type,
        "games": logs,
        "season_averages": season_avgs,
        "gp": len(logs),
    }
