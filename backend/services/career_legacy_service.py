"""Era-adjusted career summary + HOF projection.

Sprint 78 / CF3.

Pace adjustment normalizes PPG to a 100-pace baseline so cross-era
volume comparisons aren't biased by 1980s 105-pace teams vs 2010s
93-pace teams. TS% delta vs league-avg flags the player's efficiency
above the league norm of his playing era.

The HOF projection is a deliberately simple composite — see
``compute_hof_projection`` for the full point allocation. We intentionally
keep this transparent and inspectable rather than running an ML model:
fans want to see *why* a player tracks toward HOF, not a black-box score.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, SeasonStat
from models.career_legacy import EraAdjustedSummary, HofProjection


def _league_avg_pace_by_season(db: Session) -> Dict[str, float]:
    """Compute league-avg pace per season from non-playoff SeasonStat rows.

    Weighted by games-played so a low-minute call-up doesn't skew the avg.
    Falls back to a flat 100.0 for seasons missing pace data.
    """
    rows = (
        db.query(SeasonStat.season, SeasonStat.pace, SeasonStat.gp)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .filter(SeasonStat.pace.isnot(None))
        .all()
    )
    by_season: Dict[str, Tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))
    for season, pace, gp in rows:
        if pace is None:
            continue
        weight = float(gp or 1)
        cur_w, cur_v = by_season[season]
        by_season[season] = (cur_w + weight, cur_v + weight * float(pace))
    out: Dict[str, float] = {}
    for season, (w, v) in by_season.items():
        if w > 0:
            out[season] = v / w
    return out


def _league_avg_ts_by_season(db: Session) -> Dict[str, float]:
    rows = (
        db.query(SeasonStat.season, SeasonStat.ts_pct, SeasonStat.gp)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .filter(SeasonStat.ts_pct.isnot(None))
        .all()
    )
    by_season: Dict[str, Tuple[float, float]] = defaultdict(lambda: (0.0, 0.0))
    for season, ts, gp in rows:
        if ts is None:
            continue
        weight = float(gp or 1)
        cur_w, cur_v = by_season[season]
        by_season[season] = (cur_w + weight, cur_v + weight * float(ts))
    out: Dict[str, float] = {}
    for season, (w, v) in by_season.items():
        if w > 0:
            out[season] = v / w
    return out


def compute_era_adjusted_line(db: Session, player_id: int) -> EraAdjustedSummary:
    """Aggregate one player's regular-season seasons into an era-adjusted line.

    Pace-normalizes PPG and computes TS% delta vs the league baseline of
    each season the player played in. Aggregates by GP so deep-bench
    cameos don't drag the per-game line.
    """
    seasons: List[SeasonStat] = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    if not seasons:
        return EraAdjustedSummary(
            pts_pg=None,
            pts_pg_era_adj=None,
            reb_pg=None,
            ast_pg=None,
            ts_pct=None,
            ts_pct_delta_vs_league_avg=None,
            games_played=0,
            seasons_played=0,
        )

    pace_by_season = _league_avg_pace_by_season(db)
    ts_by_season = _league_avg_ts_by_season(db)

    total_gp = 0
    total_pts = 0.0
    total_pts_era = 0.0
    total_reb = 0.0
    total_ast = 0.0
    total_ts_w = 0.0
    total_ts = 0.0
    total_ts_delta_w = 0.0
    total_ts_delta = 0.0
    distinct_seasons = set()

    for row in seasons:
        gp = int(row.gp or 0)
        if gp <= 0:
            continue
        total_gp += gp
        distinct_seasons.add(row.season)
        if row.pts_pg is not None:
            total_pts += float(row.pts_pg) * gp
            league_pace = pace_by_season.get(row.season, 100.0) or 100.0
            era_factor = league_pace / 100.0 if league_pace > 0 else 1.0
            era_factor = era_factor or 1.0
            total_pts_era += (float(row.pts_pg) / era_factor) * gp
        if row.reb_pg is not None:
            total_reb += float(row.reb_pg) * gp
        if row.ast_pg is not None:
            total_ast += float(row.ast_pg) * gp
        if row.ts_pct is not None:
            total_ts_w += gp
            total_ts += float(row.ts_pct) * gp
            league_ts = ts_by_season.get(row.season)
            if league_ts is not None:
                total_ts_delta_w += gp
                total_ts_delta += (float(row.ts_pct) - league_ts) * gp

    if total_gp == 0:
        return EraAdjustedSummary(
            pts_pg=None,
            pts_pg_era_adj=None,
            reb_pg=None,
            ast_pg=None,
            ts_pct=None,
            ts_pct_delta_vs_league_avg=None,
            games_played=0,
            seasons_played=len(distinct_seasons),
        )

    return EraAdjustedSummary(
        pts_pg=round(total_pts / total_gp, 2),
        pts_pg_era_adj=round(total_pts_era / total_gp, 2),
        reb_pg=round(total_reb / total_gp, 2),
        ast_pg=round(total_ast / total_gp, 2),
        ts_pct=round(total_ts / total_ts_w, 4) if total_ts_w > 0 else None,
        ts_pct_delta_vs_league_avg=(
            round(total_ts_delta / total_ts_delta_w, 4)
            if total_ts_delta_w > 0
            else None
        ),
        games_played=total_gp,
        seasons_played=len(distinct_seasons),
    )


# ---------------------------------------------------------------------------
# HOF projection
# ---------------------------------------------------------------------------

def _career_total(seasons: List[SeasonStat], attr: str) -> int:
    total = 0
    for r in seasons:
        v = getattr(r, attr, None)
        if v is None:
            continue
        try:
            total += int(v)
        except (TypeError, ValueError):
            continue
    return total


def compute_hof_projection(
    db: Session,
    player_id: int,
    *,
    accolades: Optional[Dict[str, Any]] = None,
) -> HofProjection:
    """Composite legacy projection out of 100.

    Allocations:
      +30 if 20k career points
      +20 if MVP or DPOY
      +15 per All-Star nod (cap at +60)
      +10 if at least one championship

    When ``accolades`` is None the function falls back to deriving
    accolade counts from the local DB if/when a future awards table
    lands. For now, accolades default to zero so an unaccoladed scorer
    can still register on the points axis.

    Returns the score, the matching label band, and the top three drivers.
    """
    seasons: List[SeasonStat] = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    career_pts = _career_total(seasons, "pts")

    accolades = accolades or {}
    has_mvp = bool(accolades.get("mvp_count", 0)) or bool(accolades.get("dpoy_count", 0))
    all_star = int(accolades.get("all_star_count", 0) or 0)
    rings = int(accolades.get("championships", 0) or 0)

    drivers: List[Tuple[str, int]] = []
    score = 0

    if career_pts >= 20_000:
        score += 30
        drivers.append((f"{career_pts:,} career points (20k club)", 30))
    elif career_pts >= 15_000:
        # Partial credit when approaching but not over the line; not a
        # spec'd allocation but useful for the "Tracking" band.
        partial = int(round(30 * (career_pts - 15_000) / 5000.0))
        if partial > 0:
            score += partial
            drivers.append((f"{career_pts:,} career points (approaching 20k)", partial))

    if has_mvp:
        score += 20
        if accolades.get("mvp_count", 0):
            drivers.append((f"{int(accolades['mvp_count'])}× MVP", 20))
        else:
            drivers.append(("DPOY hardware", 20))

    if all_star > 0:
        bonus = min(all_star * 15, 60)
        score += bonus
        drivers.append((f"{all_star}× All-Star", bonus))

    if rings > 0:
        score += 10
        drivers.append((f"{rings}× champion", 10))

    score = max(0, min(100, score))

    if score >= 80:
        label = "Likely HOF"
    elif score >= 50:
        label = "Borderline"
    else:
        label = "Tracking"

    drivers.sort(key=lambda x: x[1], reverse=True)
    top_drivers = [d[0] for d in drivers[:3]]
    if not top_drivers:
        top_drivers = ["Building career resume"]

    return HofProjection(label=label, score=score, drivers=top_drivers)


def get_player_or_none(db: Session, player_id: int) -> Optional[Player]:
    return db.query(Player).filter(Player.id == player_id).first()
