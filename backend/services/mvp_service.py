"""MVP Award Race Service.

Computes a composite MVP score for the top N players in a given season using
z-score normalization across five pillars: PTS_PG, REB_PG, AST_PG, TS_PCT,
and BPM. Augments each candidate with a last-10-game trend delta so the UI
can show momentum signals.

Weights (sum to 1.0):
    pts_pg  0.30
    reb_pg  0.15
    ast_pg  0.15
    ts_pct  0.20
    bpm     0.20

Players with NULL BPM receive a neutral z-score (0.0) for that pillar —
they are not excluded from the race.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, PlayerGameLog, SeasonStat
from models.mvp import MvpCandidate, MvpRaceResponse

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MVP_WEIGHTS: Dict[str, float] = {
    "pts_pg": 0.30,
    "reb_pg": 0.15,
    "ast_pg": 0.15,
    "ts_pct": 0.20,
    "bpm":    0.20,
}

MIN_GP = 20          # minimum games played to be a candidate
TREND_WINDOW = 10    # most-recent N games for momentum calculation
HOT_THRESHOLD = 3.0  # pts_delta above this → "hot"
COLD_THRESHOLD = -3.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _zscore_pool(values: List[Optional[float]]) -> List[float]:
    """Return z-scores for a list; None → 0.0 (neutral)."""
    non_null = [v for v in values if v is not None]
    if len(non_null) < 2:
        return [0.0] * len(values)
    mu = statistics.mean(non_null)
    sigma = statistics.stdev(non_null)
    if sigma == 0:
        return [0.0] * len(values)
    return [(v - mu) / sigma if v is not None else 0.0 for v in values]


def _derive_ts_pct(row: SeasonStat) -> Optional[float]:
    """TS% = PTS / (2 * (FGA + 0.44 * FTA)).  Returns None if no shot data."""
    if row.ts_pct is not None:
        return float(row.ts_pct)
    # Derive from raw totals when the stored column is NULL
    pts = row.pts or 0
    fga = row.fga or 0
    fta = row.fta or 0
    denom = 2 * (fga + 0.44 * fta)
    if denom <= 0:
        return None
    return pts / denom


def _trend_data(
    db: Session,
    player_ids: List[int],
    season: str,
    window: int,
) -> Dict[int, Tuple[Optional[float], Optional[float], Optional[float], str, int, Optional[date]]]:
    """Batch-fetch last-`window` game logs for all player_ids in one query.

    Returns a dict keyed by player_id:
        (pts_delta, reb_delta, ast_delta, momentum, last_games, last_date)
    """
    from sqlalchemy import desc

    # Pull all regular-season logs for these players in one query, ordered newest first
    logs = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id.in_(player_ids),
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Regular Season",
        )
        .order_by(PlayerGameLog.player_id, desc(PlayerGameLog.game_date))
        .all()
    )

    # Group by player_id
    by_player: Dict[int, List[PlayerGameLog]] = defaultdict(list)
    for log in logs:
        by_player[log.player_id].append(log)

    result: Dict[int, Tuple[Optional[float], Optional[float], Optional[float], str, int, Optional[date]]] = {}

    for pid in player_ids:
        all_logs = by_player.get(pid, [])
        recent = all_logs[:window]
        n = len(recent)

        if n == 0:
            result[pid] = (None, None, None, "steady", 0, None)
            continue

        last_date = recent[0].game_date

        # Season averages from all available logs
        def _avg(attr: str, rows: List[PlayerGameLog]) -> Optional[float]:
            vals = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
            return statistics.mean(vals) if vals else None

        season_pts = _avg("pts", all_logs)
        season_reb = _avg("reb", all_logs)
        season_ast = _avg("ast", all_logs)

        recent_pts = _avg("pts", recent)
        recent_reb = _avg("reb", recent)
        recent_ast = _avg("ast", recent)

        pts_delta = (recent_pts - season_pts) if (recent_pts is not None and season_pts is not None) else None
        reb_delta = (recent_reb - season_reb) if (recent_reb is not None and season_reb is not None) else None
        ast_delta = (recent_ast - season_ast) if (recent_ast is not None and season_ast is not None) else None

        if pts_delta is not None and pts_delta > HOT_THRESHOLD:
            momentum = "hot"
        elif pts_delta is not None and pts_delta < COLD_THRESHOLD:
            momentum = "cold"
        else:
            momentum = "steady"

        result[pid] = (pts_delta, reb_delta, ast_delta, momentum, n, last_date)

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_mvp_race(db: Session, season: str, top: int = 10) -> MvpRaceResponse:
    """Return the top-N MVP candidates for *season* ranked by composite score."""

    # ------------------------------------------------------------------
    # 1. Fetch all regular-season stats meeting minimum GP threshold
    # ------------------------------------------------------------------
    rows = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= MIN_GP,
        )
        .all()
    )

    if not rows:
        return MvpRaceResponse(
            season=season,
            as_of_date=str(date.today()),
            candidates=[],
            weights=MVP_WEIGHTS,
        )

    # Deduplicate by player_id: keep the row with the most games played
    # (handles trade-deadline splits where a player appears twice)
    best: Dict[int, Tuple[SeasonStat, Player]] = {}
    for stat, player in rows:
        existing = best.get(stat.player_id)
        if existing is None or (stat.gp or 0) > (existing[0].gp or 0):
            best[stat.player_id] = (stat, player)

    stat_rows = list(best.values())
    player_ids = [p.id for _, p in stat_rows]

    # ------------------------------------------------------------------
    # 2. Z-score each pillar across the full candidate pool
    # ------------------------------------------------------------------
    def _col(attr: str) -> List[Optional[float]]:
        return [getattr(s, attr, None) for s, _ in stat_rows]

    pts_vals   = [float(s.pts_pg) if s.pts_pg is not None else None for s, _ in stat_rows]
    reb_vals   = [float(s.reb_pg) if s.reb_pg is not None else None for s, _ in stat_rows]
    ast_vals   = [float(s.ast_pg) if s.ast_pg is not None else None for s, _ in stat_rows]
    ts_vals    = [_derive_ts_pct(s) for s, _ in stat_rows]
    bpm_vals   = [float(s.bpm) if s.bpm is not None else None for s, _ in stat_rows]

    z_pts  = _zscore_pool(pts_vals)
    z_reb  = _zscore_pool(reb_vals)
    z_ast  = _zscore_pool(ast_vals)
    z_ts   = _zscore_pool(ts_vals)
    z_bpm  = _zscore_pool(bpm_vals)

    w = MVP_WEIGHTS
    raw_scores = [
        w["pts_pg"] * z_pts[i]
        + w["reb_pg"] * z_reb[i]
        + w["ast_pg"] * z_ast[i]
        + w["ts_pct"] * z_ts[i]
        + w["bpm"]    * z_bpm[i]
        for i in range(len(stat_rows))
    ]

    # Sort descending by composite score, take top-N for trend enrichment
    indexed = sorted(enumerate(raw_scores), key=lambda x: x[1], reverse=True)
    top_indices = [idx for idx, _ in indexed[:top]]
    top_scores  = [raw_scores[i] for i in top_indices]

    # Normalize scores to 0–100 relative to the best candidate
    max_score = top_scores[0] if top_scores and top_scores[0] > 0 else 1.0
    min_score = top_scores[-1] if len(top_scores) > 1 else 0.0
    score_range = max_score - min_score if max_score != min_score else 1.0

    def _normalized(raw: float) -> float:
        return round(((raw - min_score) / score_range) * 100, 1)

    # ------------------------------------------------------------------
    # 3. Fetch trend data for the top candidates in one batch query
    # ------------------------------------------------------------------
    top_player_ids = [stat_rows[i][1].id for i in top_indices]
    trend = _trend_data(db, top_player_ids, season, TREND_WINDOW)

    # ------------------------------------------------------------------
    # 4. Build response
    # ------------------------------------------------------------------
    candidates: List[MvpCandidate] = []
    latest_date: Optional[date] = None

    for rank, arr_idx in enumerate(top_indices, start=1):
        stat, player = stat_rows[arr_idx]
        raw = raw_scores[arr_idx]
        pts_delta, reb_delta, ast_delta, momentum, last_games, last_date = trend.get(
            player.id, (None, None, None, "steady", 0, None)
        )

        if last_date and (latest_date is None or last_date > latest_date):
            latest_date = last_date

        candidates.append(
            MvpCandidate(
                rank=rank,
                player_id=player.id,
                player_name=player.full_name,
                team_abbreviation=stat.team_abbreviation,
                headshot_url=player.headshot_url or "",
                gp=stat.gp or 0,
                composite_score=_normalized(raw),
                pts_pg=float(stat.pts_pg or 0),
                reb_pg=float(stat.reb_pg or 0),
                ast_pg=float(stat.ast_pg or 0),
                ts_pct=_derive_ts_pct(stat),
                bpm=float(stat.bpm) if stat.bpm is not None else None,
                pts_delta=round(pts_delta, 1) if pts_delta is not None else None,
                reb_delta=round(reb_delta, 1) if reb_delta is not None else None,
                ast_delta=round(ast_delta, 1) if ast_delta is not None else None,
                momentum=momentum,
                last_games=last_games,
            )
        )

    as_of = str(latest_date) if latest_date else str(date.today())

    return MvpRaceResponse(
        season=season,
        as_of_date=as_of,
        candidates=candidates,
        weights=MVP_WEIGHTS,
    )
