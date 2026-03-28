from __future__ import annotations

import math
import statistics
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Player, SeasonStat

router = APIRouter()

# Weights for the composite improvement score
_DELTA_WEIGHTS: list[tuple[str, float]] = [
    ("per", 2.0),
    ("bpm", 1.5),
    ("ts_pct", 1.2),
    ("pts_pg", 1.0),
    ("ast_pg", 0.8),
    ("reb_pg", 0.6),
]


def _prior_season(season: str) -> str:
    """'2024-25' → '2023-24'"""
    start, end = season.split("-")
    return f"{int(start) - 1}-{str(int(start) - 1)[2:]}"


def _stat_snapshot(row: SeasonStat) -> dict:
    return {
        "season": row.season,
        "team_abbreviation": row.team_abbreviation,
        "gp": row.gp,
        "pts_pg": row.pts_pg,
        "reb_pg": row.reb_pg,
        "ast_pg": row.ast_pg,
        "ts_pct": row.ts_pct,
        "per": row.per,
        "bpm": row.bpm,
        "usg_pct": row.usg_pct,
    }


class BreakoutSeasonStats(BaseModel):
    season: str
    team_abbreviation: str
    gp: int
    pts_pg: Optional[float] = None
    reb_pg: Optional[float] = None
    ast_pg: Optional[float] = None
    ts_pct: Optional[float] = None
    per: Optional[float] = None
    bpm: Optional[float] = None
    usg_pct: Optional[float] = None


class BreakoutEntry(BaseModel):
    player_id: int
    full_name: str
    headshot_url: Optional[str] = None
    current: BreakoutSeasonStats
    prior: BreakoutSeasonStats
    improvement_score: float
    delta_pts_pg: Optional[float] = None
    delta_reb_pg: Optional[float] = None
    delta_ast_pg: Optional[float] = None
    delta_ts_pct: Optional[float] = None
    delta_per: Optional[float] = None
    delta_bpm: Optional[float] = None


class BreakoutsResponse(BaseModel):
    season: str
    prior_season: str
    improvers: List[BreakoutEntry]
    decliners: List[BreakoutEntry]


@router.get("/breakouts", response_model=BreakoutsResponse)
def get_breakouts(
    season: str = Query("2024-25"),
    min_gp: int = Query(20),
    limit: int = Query(25),
    db: Session = Depends(get_db),
):
    """Return players showing the biggest YoY statistical improvement or decline."""
    prior = _prior_season(season)

    # Fetch current and prior season stats in two queries
    current_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= min_gp,
        )
        .all()
    )
    prior_rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == prior,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= min_gp,
        )
        .all()
    )

    # Index by player_id (keep highest-GP row when traded mid-season)
    def _best(rows: list[SeasonStat]) -> dict[int, SeasonStat]:
        out: dict[int, SeasonStat] = {}
        for r in rows:
            if r.player_id not in out or (r.gp or 0) > (out[r.player_id].gp or 0):
                out[r.player_id] = r
        return out

    current_map = _best(current_rows)
    prior_map = _best(prior_rows)

    # Players in both seasons
    shared_ids = set(current_map) & set(prior_map)

    # Compute raw deltas for all shared players
    stat_keys = [k for k, _ in _DELTA_WEIGHTS]
    records: list[dict] = []
    for pid in shared_ids:
        cur = current_map[pid]
        prv = prior_map[pid]
        deltas: dict[str, Optional[float]] = {}
        for key in stat_keys:
            cv = getattr(cur, key)
            pv = getattr(prv, key)
            deltas[key] = (cv - pv) if (cv is not None and pv is not None) else None
        records.append({"player_id": pid, "cur": cur, "prv": prv, "deltas": deltas})

    if not records:
        return BreakoutsResponse(season=season, prior_season=prior, improvers=[], decliners=[])

    # Z-score normalize each delta across all players that have it
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    for key in stat_keys:
        vals = [r["deltas"][key] for r in records if r["deltas"][key] is not None]
        if len(vals) >= 2:
            means[key] = statistics.mean(vals)
            stds[key] = statistics.stdev(vals) or 1.0
        else:
            means[key] = 0.0
            stds[key] = 1.0

    # Compute weighted improvement score for each player
    for rec in records:
        score = 0.0
        weight_sum = 0.0
        for key, weight in _DELTA_WEIGHTS:
            delta = rec["deltas"].get(key)
            if delta is not None:
                z = (delta - means[key]) / stds[key]
                score += z * weight
                weight_sum += weight
        rec["score"] = score / weight_sum if weight_sum > 0 else 0.0

    # Sort: improvers = highest score, decliners = lowest score
    records.sort(key=lambda r: r["score"], reverse=True)

    # Fetch player metadata
    all_ids = [r["player_id"] for r in records]
    players_map: dict[int, Player] = {
        p.id: p
        for p in db.query(Player).filter(Player.id.in_(all_ids)).all()
    }

    def _build_entry(rec: dict) -> BreakoutEntry:
        pid = rec["player_id"]
        player = players_map.get(pid)
        d = rec["deltas"]
        # Normalize improvement_score to 0–100 range for display
        raw = rec["score"]
        display_score = round(50 + raw * 10, 1)  # centered at 50, 1 std ≈ 10 pts

        return BreakoutEntry(
            player_id=pid,
            full_name=player.full_name if player else str(pid),
            headshot_url=player.headshot_url if player else None,
            current=BreakoutSeasonStats(**_stat_snapshot(rec["cur"])),
            prior=BreakoutSeasonStats(**_stat_snapshot(rec["prv"])),
            improvement_score=display_score,
            delta_pts_pg=round(d["pts_pg"], 2) if d.get("pts_pg") is not None else None,
            delta_reb_pg=round(d["reb_pg"], 2) if d.get("reb_pg") is not None else None,
            delta_ast_pg=round(d["ast_pg"], 2) if d.get("ast_pg") is not None else None,
            delta_ts_pct=round(d["ts_pct"], 4) if d.get("ts_pct") is not None else None,
            delta_per=round(d["per"], 2) if d.get("per") is not None else None,
            delta_bpm=round(d["bpm"], 2) if d.get("bpm") is not None else None,
        )

    improvers = [_build_entry(r) for r in records[:limit]]
    decliners = [_build_entry(r) for r in records[-limit:][::-1]]

    return BreakoutsResponse(
        season=season,
        prior_season=prior,
        improvers=improvers,
        decliners=decliners,
    )
