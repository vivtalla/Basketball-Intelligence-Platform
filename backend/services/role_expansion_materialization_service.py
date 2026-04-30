"""Sprint 79 Stream A2 — materialize role_expansion_observations from season_stats.

Scans the season_stats table for (player_id, season) pairs where:
  - usg_pct(season) - usg_pct(season-1) >= MIN_USG_DELTA  (default +0.03)
  - both seasons have gp >= MIN_GP                          (default 40)
  - both seasons are regular-season rows (is_playoff=False)
  - both seasons have non-null ts_pct + usg_pct

For each qualifying pair, computes:
  - usg_delta, pre_ts_pct, post_ts_pct, ts_delta
  - pre_ast_rate (ast_pg / min_pg * 36, when min_pg > 0)
  - pre_obpm (verbatim from season_stats)
  - pre_age (parsed from Player.birth_date as of from_season's start year)
  - pre_role_archetype (from classify_player_archetype)

Idempotent: per-pair upsert on (player_id, from_season, to_season). Re-run
produces zero net new rows when source data is unchanged.

Methodology spec: ``specs/methodology-future-modeling.md#2``.
Acceptance: >= 10 seasons of pairs (~350 obs); idempotent re-run; backtest
MAE <= 0.025 TS%.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import Player, RoleExpansionObservation, SeasonStat
from services.player_archetype_service import classify_player_archetype, parse_age_as_of_season

log = logging.getLogger(__name__)

MIN_USG_DELTA = 0.03   # 3 percentage points (matches spec)
MIN_GP = 40            # both pre and post seasons must clear this
MIN_TS_PCT = 0.30      # sanity floor — anything below is noise (FT-only seasons)
MAX_TS_PCT = 0.95      # sanity ceiling — anything above is data error


def _season_to_year(season: str) -> Optional[int]:
    """Convert '2024-25' -> 2024 (the start year)."""
    try:
        return int(season.split("-")[0])
    except (ValueError, AttributeError, IndexError):
        return None


def _consecutive(prev_season: str, curr_season: str) -> bool:
    """True if curr is exactly one year after prev."""
    p, c = _season_to_year(prev_season), _season_to_year(curr_season)
    return p is not None and c is not None and c == p + 1


def _aggregate_player_season(rows: List[SeasonStat]) -> Optional[Dict[str, float]]:
    """When a player was traded mid-season, season_stats has multiple rows
    (one per team). Aggregate by GP-weighted average for percentage stats and
    sum for counting stats. Returns None if combined sample is too thin.
    """
    total_gp = sum((r.gp or 0) for r in rows)
    if total_gp < MIN_GP:
        return None

    def _weighted_avg(field: str) -> Optional[float]:
        weighted_sum = 0.0
        weight = 0
        for row in rows:
            value = getattr(row, field, None)
            if value is None:
                continue
            gp = row.gp or 0
            if gp <= 0:
                continue
            weighted_sum += value * gp
            weight += gp
        return (weighted_sum / weight) if weight > 0 else None

    ts_pct = _weighted_avg("ts_pct")
    usg_pct = _weighted_avg("usg_pct")
    if ts_pct is None or usg_pct is None:
        return None
    if not (MIN_TS_PCT <= ts_pct <= MAX_TS_PCT):
        return None

    ast_pg = _weighted_avg("ast_pg")
    min_pg = _weighted_avg("min_pg")
    obpm = _weighted_avg("obpm")

    ast_rate = (ast_pg / min_pg * 36.0) if (ast_pg is not None and min_pg and min_pg > 0) else None

    return {
        "gp": float(total_gp),
        "ts_pct": ts_pct,
        "usg_pct": usg_pct,
        "ast_rate": ast_rate,
        "obpm": obpm,
        "min_pg": min_pg,
    }


def _archetype_for(db: Session, player_id: int, season: str) -> Optional[str]:
    try:
        result = classify_player_archetype(db, player_id, season, season_type="Regular Season")
        return result.archetype_key if result else None
    except Exception:
        # Archetype classification can fail if the player has incomplete frame data.
        # Don't block materialization — just leave archetype null for KNN to filter on.
        return None


def materialize_role_expansion(
    db: Optional[Session] = None,
    *,
    min_usg_delta: float = MIN_USG_DELTA,
    min_gp: int = MIN_GP,
) -> Dict[str, int]:
    """Walk season_stats, identify role-expansion pairs, upsert to the table.

    Returns: {pairs_found, rows_inserted, rows_updated, rows_skipped, players_processed}.
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    inserted = 0
    updated = 0
    skipped = 0
    players_processed = 0

    try:
        # Group regular-season rows by player_id, then by season (for traded players).
        rows = (
            db.query(SeasonStat)
            .filter(SeasonStat.is_playoff == False)
            .order_by(SeasonStat.player_id.asc(), SeasonStat.season.asc())
            .all()
        )

        by_player: Dict[int, Dict[str, List[SeasonStat]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            by_player[row.player_id][row.season].append(row)

        now = datetime.utcnow()

        for player_id, season_map in by_player.items():
            players_processed += 1
            seasons_sorted = sorted(season_map.keys())
            if len(seasons_sorted) < 2:
                continue

            # Aggregate each season once (avoids recomputing inside the inner loop).
            agg_by_season: Dict[str, Optional[Dict[str, float]]] = {
                s: _aggregate_player_season(season_map[s]) for s in seasons_sorted
            }

            player = db.query(Player).filter_by(id=player_id).first()
            birth_date = player.birth_date if player else None

            for i in range(1, len(seasons_sorted)):
                prev_season = seasons_sorted[i - 1]
                curr_season = seasons_sorted[i]

                if not _consecutive(prev_season, curr_season):
                    continue

                pre = agg_by_season.get(prev_season)
                post = agg_by_season.get(curr_season)
                if not pre or not post:
                    skipped += 1
                    continue
                if pre["gp"] < min_gp or post["gp"] < min_gp:
                    skipped += 1
                    continue

                usg_delta = post["usg_pct"] - pre["usg_pct"]
                if usg_delta < min_usg_delta:
                    continue

                ts_delta = post["ts_pct"] - pre["ts_pct"]
                pre_age = parse_age_as_of_season(birth_date, prev_season)
                pre_archetype = _archetype_for(db, player_id, prev_season)

                existing = (
                    db.query(RoleExpansionObservation)
                    .filter_by(
                        player_id=player_id,
                        from_season=prev_season,
                        to_season=curr_season,
                    )
                    .first()
                )

                if existing is None:
                    obs = RoleExpansionObservation(
                        player_id=player_id,
                        from_season=prev_season,
                        to_season=curr_season,
                        usg_delta=usg_delta,
                        pre_ts_pct=pre["ts_pct"],
                        post_ts_pct=post["ts_pct"],
                        ts_delta=ts_delta,
                        pre_ast_rate=pre.get("ast_rate"),
                        pre_obpm=pre.get("obpm"),
                        pre_age=pre_age,
                        pre_role_archetype=pre_archetype,
                        computed_at=now,
                    )
                    db.add(obs)
                    try:
                        db.flush()
                        inserted += 1
                    except Exception:
                        db.rollback()
                        skipped += 1
                else:
                    existing.usg_delta = usg_delta
                    existing.pre_ts_pct = pre["ts_pct"]
                    existing.post_ts_pct = post["ts_pct"]
                    existing.ts_delta = ts_delta
                    existing.pre_ast_rate = pre.get("ast_rate")
                    existing.pre_obpm = pre.get("obpm")
                    existing.pre_age = pre_age
                    existing.pre_role_archetype = pre_archetype
                    existing.computed_at = now
                    updated += 1

        db.commit()
    finally:
        if own_session:
            db.close()

    summary = {
        "pairs_found": inserted + updated,
        "rows_inserted": inserted,
        "rows_updated": updated,
        "rows_skipped": skipped,
        "players_processed": players_processed,
    }
    log.info("role_expansion materialization complete: %s", summary)
    return summary
