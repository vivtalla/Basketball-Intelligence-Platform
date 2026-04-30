"""Sprint 78 FO4 — Aging Curve Service.

Empirical NBA aging curves derived from historical SeasonStat rows. We bucket
players by primary position (G / F / C) and, for each integer age, average a
few rate-style metrics (pts_pg, ts_pct, win-shares-per-48, min_pg, usg_pct)
across all seasons in the database. The resulting curve is the *expected*
year-on-year trajectory; ``project_player_next_n`` applies that delta to a
player's most recent season to forecast future seasons.

Notes
-----
* Regular-season rows only (``is_playoff=False``).
* Each player contributes at most one row per (age, season) — when a player is
  traded mid-season we keep the highest-GP row to avoid double counting.
* If a position bucket is sparse (<25 player-seasons total or <3 ages
  represented) we fall back to the global "all" curve. This keeps centers and
  late-career outliers from producing degenerate projections.
* Curves are cached in-process with a simple module-level dict, keyed by the
  position bucket. Tests can call ``clear_aging_curve_cache()`` between cases.

The service is intentionally dependency-free beyond SQLAlchemy — no numpy,
no pandas, no external curve library — so it runs anywhere the existing
backend runs.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, SeasonStat
from models.team_arc import AgingCurvePoint, AgingCurveResponse, ProjectedSeason


_POSITION_BUCKET_MAP: Dict[str, str] = {
    "pg": "G", "sg": "G", "g": "G", "guard": "G",
    "sf": "F", "pf": "F", "f": "F", "forward": "F",
    "c": "C", "center": "C",
    "g-f": "G", "f-g": "F", "f-c": "F", "c-f": "C",
}

_CURVE_CACHE: Dict[str, AgingCurveResponse] = {}


def position_bucket(position: Optional[str]) -> str:
    """Normalize a free-form position string to G/F/C/all.

    Players with multi-position labels (e.g. ``"F-C"``) bucket to the first
    listed slot. Empty / unknown positions return ``"all"``.
    """
    if not position:
        return "all"
    key = position.lower().strip().split("-")[0]
    return _POSITION_BUCKET_MAP.get(key, "all")


def _season_start_year(season: Optional[str]) -> Optional[int]:
    if not season or "-" not in season:
        return None
    try:
        return int(season.split("-")[0])
    except (ValueError, TypeError):
        return None


def _birth_year(player: Player) -> Optional[int]:
    """Best-effort extraction of birth year from Player.birth_date.

    Birth date is a free-form string in the existing schema. We accept ISO
    (``YYYY-MM-DD``) and ``MM/DD/YYYY`` shapes and otherwise return None.
    """
    if not player.birth_date:
        return None
    raw = str(player.birth_date).strip()
    # ISO YYYY-MM-DD
    if len(raw) >= 4 and raw[:4].isdigit():
        try:
            return int(raw[:4])
        except ValueError:
            return None
    # MM/DD/YYYY
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 3 and parts[-1].isdigit():
            try:
                return int(parts[-1])
            except ValueError:
                return None
    return None


def _player_age_at_season(player: Player, season: str) -> Optional[int]:
    """Player age on Feb 1 of the *first* calendar year of the season.

    Feb 1 lands inside every NBA regular season, which makes it a natural
    reference point for a season-level age. Returns None if birth-date
    parsing fails.
    """
    birth_year = _birth_year(player)
    season_year = _season_start_year(season)
    if birth_year is None or season_year is None:
        return None
    # Approximate: assume birth before Feb 1 of the season's first year.
    # Subtle off-by-one is fine for aggregate curves.
    return season_year + 1 - birth_year


def _ws_per_48(stat: SeasonStat) -> Optional[float]:
    if stat.ws is None or not stat.min_total or stat.min_total <= 0:
        return None
    return float(stat.ws) * 48.0 / float(stat.min_total)


def _build_curve_for_bucket(
    db: Session,
    target_bucket: str,
) -> AgingCurveResponse:
    """Compute an aging curve from every historical SeasonStat row matching
    ``target_bucket``. ``target_bucket="all"`` ignores position filtering.
    """
    rows = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .all()
    )

    # Bucket rows by age, keeping highest-GP row per (player, season).
    by_player_season: Dict[Tuple[int, str], Tuple[SeasonStat, Player]] = {}
    for stat, player in rows:
        if target_bucket != "all" and position_bucket(player.position) != target_bucket:
            continue
        key = (stat.player_id, stat.season)
        existing = by_player_season.get(key)
        if existing is None or (stat.gp or 0) > (existing[0].gp or 0):
            by_player_season[key] = (stat, player)

    age_buckets: Dict[int, List[Tuple[SeasonStat, Player]]] = defaultdict(list)
    seasons_used: set = set()
    for stat, player in by_player_season.values():
        age = _player_age_at_season(player, stat.season)
        if age is None or age < 18 or age > 45:
            continue
        # Require some real minutes to avoid garbage-time biased rows.
        if stat.gp is None or stat.gp < 10:
            continue
        age_buckets[age].append((stat, player))
        seasons_used.add(stat.season)

    points: List[AgingCurvePoint] = []
    for age in sorted(age_buckets.keys()):
        rows_for_age = age_buckets[age]
        if not rows_for_age:
            continue

        def _avg(getter) -> Optional[float]:
            values = [getter(s) for s, _ in rows_for_age]
            values = [v for v in values if v is not None]
            if not values:
                return None
            return sum(values) / float(len(values))

        points.append(AgingCurvePoint(
            age=age,
            sample_size=len(rows_for_age),
            pts_pg=_avg(lambda s: s.pts_pg),
            ts_pct=_avg(lambda s: s.ts_pct),
            ws_per_48=_avg(_ws_per_48),
            min_pg=_avg(lambda s: s.min_pg),
            usg_pct=_avg(lambda s: s.usg_pct),
        ))

    return AgingCurveResponse(
        position_bucket=target_bucket,
        seasons_used=len(seasons_used),
        points=points,
    )


def compute_aging_curve(
    db: Session,
    position: Optional[str] = None,
) -> AgingCurveResponse:
    """Compute (or read from cache) the empirical aging curve for ``position``.

    ``position`` may be a raw position string (``"PG"``, ``"F-C"``) or a bucket
    label (``"G"``, ``"F"``, ``"C"``, ``"all"``). Sparse buckets fall back to
    the ``"all"`` curve.
    """
    bucket = position_bucket(position) if position else "all"

    if bucket in _CURVE_CACHE:
        return _CURVE_CACHE[bucket]

    curve = _build_curve_for_bucket(db, bucket)
    # Fall back to "all" if the bucket is too sparse.
    if bucket != "all" and (
        sum(point.sample_size for point in curve.points) < 25
        or len(curve.points) < 3
    ):
        if "all" not in _CURVE_CACHE:
            _CURVE_CACHE["all"] = _build_curve_for_bucket(db, "all")
        curve = _CURVE_CACHE["all"]

    _CURVE_CACHE[bucket] = curve
    return curve


def clear_aging_curve_cache() -> None:
    """Drop the in-process curve cache. Intended for tests."""
    _CURVE_CACHE.clear()


def _curve_lookup(curve: AgingCurveResponse) -> Dict[int, AgingCurvePoint]:
    return {point.age: point for point in curve.points}


def _delta(
    curve_index: Dict[int, AgingCurvePoint],
    base_age: int,
    next_age: int,
    field: str,
) -> Optional[float]:
    """Multiplicative delta between two adjacent ages on a curve.

    Returns ``next_value / base_value`` (a ratio) so we can apply it to a
    player's actual current value. Falls back to neighbor ages if the exact
    age is missing in the curve.
    """
    base_point = curve_index.get(base_age)
    next_point = curve_index.get(next_age)
    if base_point is None:
        # Walk down to the closest younger point.
        for age in sorted(curve_index.keys()):
            if age <= base_age:
                base_point = curve_index[age]
        if base_point is None:
            return None
    if next_point is None:
        for age in sorted(curve_index.keys()):
            if age >= next_age:
                next_point = curve_index[age]
                break
        if next_point is None:
            return None
    base_value = getattr(base_point, field)
    next_value = getattr(next_point, field)
    if base_value is None or next_value is None or base_value == 0:
        return None
    return float(next_value) / float(base_value)


def project_player_next_n(
    db: Session,
    player_id: int,
    n_years: int = 3,
    base_season: Optional[str] = None,
) -> List[ProjectedSeason]:
    """Project a single player forward ``n_years`` seasons using the empirical
    aging curve for their position.

    Year 0 is the player's most recent (or ``base_season``) line. Years 1..n
    apply the multiplicative delta between adjacent ages on the position's
    aging curve. If the player's age cannot be inferred we fall back to a flat
    projection that simply repeats the current values.
    """
    player = db.query(Player).filter(Player.id == player_id).first()
    if player is None:
        return []

    stats_query = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
    )
    if base_season:
        stats_query = stats_query.filter(SeasonStat.season == base_season)
    stats = stats_query.order_by(SeasonStat.season.desc()).all()
    if not stats:
        return []

    # Pick the highest-GP row for the latest season (handles mid-season trades).
    latest_season = stats[0].season
    season_rows = [s for s in stats if s.season == latest_season]
    base_stat = max(season_rows, key=lambda s: s.gp or 0)

    base_age = _player_age_at_season(player, base_stat.season)
    curve = compute_aging_curve(db, player.position)
    curve_index = _curve_lookup(curve)

    out: List[ProjectedSeason] = []
    base_year = _season_start_year(base_stat.season) or 0

    current_pts = float(base_stat.pts_pg or 0.0)
    current_ts = float(base_stat.ts_pct) if base_stat.ts_pct is not None else None
    current_ws48 = _ws_per_48(base_stat)
    current_min = float(base_stat.min_pg or 0.0)
    current_usg = float(base_stat.usg_pct) if base_stat.usg_pct is not None else None

    for offset in range(0, max(0, int(n_years)) + 1):
        if base_age is not None:
            age = base_age + offset
        else:
            age = -1

        if offset == 0:
            pts = current_pts
            ts = current_ts
            ws48 = current_ws48
            min_pg = current_min
            usg = current_usg
        else:
            if base_age is None:
                # No age info: hold flat.
                pts, ts, ws48, min_pg, usg = current_pts, current_ts, current_ws48, current_min, current_usg
            else:
                ratio_pts = _delta(curve_index, age - 1, age, "pts_pg") or 1.0
                ratio_ts = _delta(curve_index, age - 1, age, "ts_pct") or 1.0
                ratio_ws = _delta(curve_index, age - 1, age, "ws_per_48") or 1.0
                ratio_min = _delta(curve_index, age - 1, age, "min_pg") or 1.0
                ratio_usg = _delta(curve_index, age - 1, age, "usg_pct") or 1.0
                # Apply gentle clamp to keep projections sane.
                ratio_pts = max(0.4, min(1.4, ratio_pts))
                ratio_ts = max(0.85, min(1.15, ratio_ts))
                ratio_ws = max(0.4, min(1.4, ratio_ws))
                ratio_min = max(0.5, min(1.2, ratio_min))
                ratio_usg = max(0.6, min(1.3, ratio_usg))
                current_pts = current_pts * ratio_pts
                current_min = current_min * ratio_min
                if current_ts is not None:
                    current_ts = current_ts * ratio_ts
                if current_ws48 is not None:
                    current_ws48 = current_ws48 * ratio_ws
                if current_usg is not None:
                    current_usg = current_usg * ratio_usg
                pts = current_pts
                ts = current_ts
                ws48 = current_ws48
                min_pg = current_min
                usg = current_usg

        # Win-share total approximation: ws_per_48 * (min_pg * gp).
        # We assume a healthy 70-game ceiling that decays with age past 33.
        if base_age is not None and age > 33:
            assumed_gp = max(40.0, 70.0 - (age - 33) * 4.0)
        else:
            assumed_gp = 70.0
        ws_total: Optional[float] = None
        if ws48 is not None and min_pg is not None:
            ws_total = ws48 * min_pg * assumed_gp / 48.0

        out.append(ProjectedSeason(
            player_id=player_id,
            player_name=player.full_name,
            age=age if age >= 0 else 0,
            year_offset=offset,
            pts_pg=round(pts, 2) if pts is not None else None,
            ts_pct=round(ts, 4) if ts is not None else None,
            ws_per_48=round(ws48, 4) if ws48 is not None else None,
            min_pg=round(min_pg, 2) if min_pg is not None else None,
            usg_pct=round(usg, 2) if usg is not None else None,
            win_share_total=round(ws_total, 2) if ws_total is not None else None,
            notes=None,
        ))

    return out
