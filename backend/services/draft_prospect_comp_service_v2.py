"""Sprint 100 (Stream C) — outcome-weighted NBA comp service v2.

Differences vs v1 (``draft_prospect_comp_service.py``):

  1. **Outcome weighting.** When historical ``DraftOutcome`` rows exist
     for a candidate's player_id, similarity gets a small weighted lift
     for comps that "panned out" (starter+) and a small cut for busts.
     This is intentionally a SMALL effect (±10% on similarity score)
     so feature distance still dominates — outcome bias is a tiebreaker,
     not a re-rank.

  2. **Confidence band on each comp.** Each result gets a ``confidence``
     (high/medium/low) based on (a) absolute feature distance, and (b)
     how many neighbours from the historical baseline share the same
     outcome tier — a tight cluster ⇒ high confidence; a noisy
     neighbourhood ⇒ low.

  3. **Outcome tier surfaced on each comp.** When the comp player has
     an entry in ``draft_outcomes``, ``outcome_tier`` + a short
     ``career_summary`` go on the response. v1 only carried season-N
     averages; v2 also returns career-aggregate context.

The Mahalanobis-distance option from the plan is **deferred** — with a
small comp pool (current season NBA players) the inverse-covariance
matrix is unstable. We document the path in a function stub
(``mahalanobis_distance``) and revisit once the historical baseline is
big enough.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import DraftOutcome, DraftProspect, Player, SeasonStat
from services.draft_translation_service import translate_prospect_to_nba

logger = logging.getLogger(__name__)


# Feature weights — same as v1; tuned to the available comp features.
FEATURE_WEIGHTS: Dict[str, float] = {
    "pts": 1.5, "reb": 1.3, "ast": 1.3,
    "stl": 0.7, "blk": 0.7, "tov": 0.7,
    "ts_pct": 1.2, "usg_pct": 1.2,
}

# Active NBA comp pool — current season + previous, for breadth without
# pulling 30 years of data into memory.
COMP_POOL_SEASONS: Tuple[str, ...] = ("2025-26", "2024-25")
MIN_GP = 30

# Sprint 104 (Stream B) — position-aware comp weighting. When a candidate
# shares the prospect's position bucket, similarity gets a +5 additive
# boost (capped at 99). Bucketing collapses positions into the three
# coarse families G/F/C.
#
# Handles two formats coexisting in the platform:
#   - Abbreviated (DraftProspect.primary_position): "PG"/"SG"/"SF"/"PF"/"C".
#   - NBA-API style (Player.position):              "Guard"/"Forward"/"Center"
#     and hyphenated combos like "Guard-Forward". We take the first word
#     (left of the hyphen) as the primary bucket.
_POSITION_BUCKETS: Dict[str, str] = {
    "PG": "G", "SG": "G", "G": "G", "GUARD": "G",
    "SF": "F", "PF": "F", "F": "F", "FORWARD": "F",
    "C": "C", "CENTER": "C",
}
POSITION_MATCH_BONUS = 5.0
SIMILARITY_CAP = 99.0


def _position_bucket(pos: Optional[str]) -> Optional[str]:
    if not pos:
        return None
    # Strip hyphenated combos to the primary (leftmost) position so
    # "Guard-Forward" → "GUARD" → G.
    primary = pos.strip().upper().split("-")[0].strip()
    return _POSITION_BUCKETS.get(primary)


# ── Feature extraction ───────────────────────────────────────────────


def _player_features(stat: SeasonStat) -> Optional[Dict[str, float]]:
    # SeasonStat ORM uses `gp` / `*_pg` (Sprint 80+ canonical names);
    # earlier comp v2 code referenced `games_played` / `*_per_game` which
    # don't exist on the model — that made historical_comps silently
    # come back empty in production. Pull from the right columns.
    if (stat.gp or 0) < MIN_GP:
        return None
    return {
        "pts": float(stat.pts_pg or 0.0),
        "reb": float(stat.reb_pg or 0.0),
        "ast": float(stat.ast_pg or 0.0),
        "stl": float(stat.stl_pg or 0.0),
        "blk": float(stat.blk_pg or 0.0),
        "tov": float(stat.tov_pg or 0.0),
        "ts_pct": float(stat.ts_pct or 0.0),
        "usg_pct": float(stat.usg_pct or 0.0),
    }


def _build_pool(db: Session) -> List[Tuple[int, str, str, Dict[str, float], Optional[str]]]:
    """Return ``[(player_id, player_name, season, features, position_bucket), ...]``.

    Filtered to ``MIN_GP`` games and the two most-recent NBA seasons.
    Position bucket is derived from ``Player.position`` and may be None
    for players with unknown position.
    """
    pool: List[Tuple[int, str, str, Dict[str, float], Optional[str]]] = []
    rows = (
        db.query(SeasonStat, Player)
        .join(Player, SeasonStat.player_id == Player.id)
        .filter(SeasonStat.season.in_(COMP_POOL_SEASONS))
        .filter(SeasonStat.is_playoff.is_(False))
        .all()
    )
    for stat, player in rows:
        feats = _player_features(stat)
        if feats is None:
            continue
        pool.append((player.id, player.full_name, stat.season, feats, _position_bucket(player.position)))
    return pool


def _zscore_pool(pool_features: List[Dict[str, float]]) -> Dict[str, Tuple[float, float]]:
    """Compute (mean, stddev) per feature over the pool."""
    if not pool_features:
        return {}
    out: Dict[str, Tuple[float, float]] = {}
    for key in FEATURE_WEIGHTS:
        values = [f.get(key, 0.0) for f in pool_features]
        n = len(values)
        mean = sum(values) / n
        var = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
        stddev = var ** 0.5
        out[key] = (mean, stddev if stddev > 1e-6 else 1.0)
    return out


def _weighted_z_distance(
    target: Dict[str, float],
    candidate: Dict[str, float],
    stats: Dict[str, Tuple[float, float]],
) -> float:
    """Weighted z-score Euclidean distance."""
    s = 0.0
    for key, weight in FEATURE_WEIGHTS.items():
        mean, std = stats[key]
        dt = (target.get(key, 0.0) - mean) / std
        dc = (candidate.get(key, 0.0) - mean) / std
        s += weight * (dt - dc) ** 2
    return s ** 0.5


def _outcome_for_player(db: Session, player_id: int) -> Optional[DraftOutcome]:
    return (
        db.query(DraftOutcome)
        .filter(DraftOutcome.player_id == player_id)
        .order_by(DraftOutcome.id.desc())
        .first()
    )


def _outcome_weight(outcome: Optional[DraftOutcome]) -> float:
    """Map outcome tier to ±10% similarity weight."""
    if outcome is None or outcome.outcome_tier is None:
        return 1.0
    tier = outcome.outcome_tier
    if tier in ("superstar", "star"):
        return 0.92  # smaller distance → higher similarity
    if tier == "starter":
        return 0.97
    if tier == "bust":
        return 1.08  # larger distance → lower similarity
    return 1.0


def _career_summary(outcome: Optional[DraftOutcome]) -> Optional[Dict[str, Any]]:
    if outcome is None:
        return None
    return {
        "games": outcome.career_games,
        "minutes": outcome.career_minutes,
        "ppg": outcome.career_ppg,
        "career_ws": outcome.career_ws,
        "all_star": outcome.all_star_selections,
        "all_nba": outcome.all_nba_selections,
        "tier": outcome.outcome_tier,
    }


def find_nba_comps_v2(
    db: Session,
    prospect_id: int,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Return ``top_k`` NBA comps with outcome context and a confidence band."""
    translation = translate_prospect_to_nba(db, prospect_id)
    if translation is None:
        return []

    # Sprint 104 (Stream B) — pull prospect position for position-aware boost.
    prospect = db.query(DraftProspect).filter(DraftProspect.id == prospect_id).first()
    prospect_bucket = _position_bucket(prospect.primary_position) if prospect else None

    target = {
        "pts": float(translation.projected_pts_per100 or 0.0),
        "reb": float(translation.projected_reb_per100 or 0.0),
        "ast": float(translation.projected_ast_per100 or 0.0),
        "stl": float(translation.projected_stl_per100 or 0.0),
        "blk": float(translation.projected_blk_per100 or 0.0),
        "tov": float(translation.projected_tov_per100 or 0.0),
        "ts_pct": float(translation.projected_ts_pct or 0.0),
        "usg_pct": float(translation.projected_usg_pct or 0.0),
    }

    pool = _build_pool(db)
    if not pool:
        return []
    stats = _zscore_pool([f for _, _, _, f, _ in pool])

    scored: List[Tuple[float, int, str, str, Dict[str, float], Optional[DraftOutcome], Optional[str]]] = []
    for player_id, player_name, season, feats, candidate_bucket in pool:
        d = _weighted_z_distance(target, feats, stats)
        outcome = _outcome_for_player(db, player_id)
        adjusted = d * _outcome_weight(outcome)
        scored.append((adjusted, player_id, player_name, season, feats, outcome, candidate_bucket))

    scored.sort(key=lambda r: r[0])
    top = scored[:top_k]
    if not top:
        return []

    # Map distance → 0..100 similarity, with the closest comp anchored at 95.
    closest = top[0][0]
    farthest = top[-1][0] if len(top) > 1 else closest + 1.0
    spread = max(farthest - closest, 1e-6)

    def _sim(d: float) -> float:
        # Tightest 95; loosest 60; linear in between.
        norm = 1.0 - (d - closest) / spread if spread > 0 else 1.0
        return round(60.0 + 35.0 * norm, 2)

    # Confidence — based on neighbourhood tier homogeneity.
    tiers_in_top = [o.outcome_tier for _, _, _, _, _, o, _ in top if o is not None]
    if len(tiers_in_top) >= 3 and len(set(tiers_in_top)) <= 2:
        neighbourhood_confidence = "high"
    elif len(tiers_in_top) >= 2:
        neighbourhood_confidence = "medium"
    else:
        neighbourhood_confidence = "low"

    results: List[Dict[str, Any]] = []
    for d, pid, name, season, feats, outcome, candidate_bucket in top:
        base_similarity = _sim(d)
        # Sprint 104 (Stream B) — additive position-bucket bonus (capped).
        position_match = (
            prospect_bucket is not None
            and candidate_bucket is not None
            and prospect_bucket == candidate_bucket
        )
        if position_match:
            similarity = min(SIMILARITY_CAP, base_similarity + POSITION_MATCH_BONUS)
            rationale = "matched on position + skill profile"
        else:
            similarity = base_similarity
            rationale = "matched on skill profile"

        results.append({
            "player_id": pid,
            "player_name": name,
            "season": season,
            "similarity": round(similarity, 2),
            "outcome_tier": outcome.outcome_tier if outcome else None,
            "career_summary": _career_summary(outcome),
            "neighbourhood_confidence": neighbourhood_confidence,
            "position_bucket": candidate_bucket,
            "position_match": position_match,
            "rationale": rationale,
            "pts_pg": round(feats["pts"], 2),
            "reb_pg": round(feats["reb"], 2),
            "ast_pg": round(feats["ast"], 2),
            "ts_pct": round(feats["ts_pct"], 3),
            "usg_pct": round(feats["usg_pct"], 3),
        })
    return results


def mahalanobis_distance(*args, **kwargs):  # pragma: no cover
    """Deferred. See module docstring."""
    raise NotImplementedError(
        "Mahalanobis comp distance is deferred to Sprint 101 once the "
        "historical baseline supports a stable covariance estimate."
    )
