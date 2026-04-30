"""Sprint 79 Stream A2 — opportunity_v2 uplift KNN.

For a target player T (current season pre-bump features), find K nearest
neighbors in role_expansion_observations whose archetype matches T's and
whose pre-bump ts_pct is within +/-0.04 of T's. Return the empirical
distribution of ts_delta across those neighbors as an evidence band.

Methodology spec: ``specs/methodology-future-modeling.md#2``.

The KNN computes shrunk-Mahalanobis distance over a 5-feature space:
  (usg_delta, pre_ts_pct, pre_ast_rate, pre_obpm, pre_age)

Distance is computed against the population of usable historical observations
each request — small dataset (~300 rows) so the per-call cost is negligible.
The `usg_delta` axis weights similarity by *how big* the historical bump was,
which is desirable: a player about to take on +6pp matches better with
historical +6pp cases than with historical +3pp cases.
"""

from __future__ import annotations

import logging
from statistics import mean
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, RoleExpansionObservation
from models.insights import OpportunityUplift, OpportunityUpliftComparable
from services.reliability_service import (
    covariance_matrix,
    invert_matrix,
    mahalanobis_distance,
    shrunk_covariance,
)

log = logging.getLogger(__name__)

# Spec-defined thresholds
K_NEIGHBORS = 20
TS_WINDOW = 0.04                    # +/-0.04 TS% archetype-match window
MIN_NEIGHBORS_FOR_RESULT = 5        # below this, return None (subject too unique)
HIGH_CONFIDENCE_N = 15
MEDIUM_CONFIDENCE_N = 8
SHRINKAGE = 0.20                    # similarity_v3 default for shrunk covariance

_FEATURE_KEYS = ("usg_delta", "pre_ts_pct", "pre_ast_rate", "pre_obpm", "pre_age")


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Simple linear-interp percentile on a pre-sorted list. pct in [0, 100]."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = rank - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def _confidence_band(n: int) -> str:
    if n >= HIGH_CONFIDENCE_N:
        return "high"
    if n >= MEDIUM_CONFIDENCE_N:
        return "medium"
    return "low"


def _features_complete(obs: RoleExpansionObservation) -> bool:
    """Every neighbor must have all 5 features for Mahalanobis to work."""
    return all(getattr(obs, k, None) is not None for k in _FEATURE_KEYS)


def _vector(obs: RoleExpansionObservation) -> List[float]:
    return [float(getattr(obs, k)) for k in _FEATURE_KEYS]


def compute_uplift(
    db: Session,
    *,
    target_archetype: Optional[str],
    target_ts_pct: Optional[float],
    target_usg_delta: float,
    target_ast_rate: Optional[float],
    target_obpm: Optional[float],
    target_age: Optional[int],
) -> Optional[OpportunityUplift]:
    """KNN over role_expansion_observations. Returns None when neighbor count < 5.

    Caller supplies the target's *projected* usg_delta — typically derived from
    Opportunity score (e.g., +0.04 for a "primed for expansion" candidate).
    """
    if target_archetype is None or target_ts_pct is None:
        return None
    if any(v is None for v in (target_ast_rate, target_obpm, target_age)):
        # Without the full feature set, distance is not well-defined.
        return None

    # Tier 1: archetype match + ts_pct window (strict)
    candidates = (
        db.query(RoleExpansionObservation)
        .filter(
            RoleExpansionObservation.pre_role_archetype == target_archetype,
            RoleExpansionObservation.pre_ts_pct >= target_ts_pct - TS_WINDOW,
            RoleExpansionObservation.pre_ts_pct <= target_ts_pct + TS_WINDOW,
        )
        .all()
    )
    candidates = [c for c in candidates if _features_complete(c)]
    if len(candidates) < MIN_NEIGHBORS_FOR_RESULT:
        return None

    target_vec = [
        float(target_usg_delta),
        float(target_ts_pct),
        float(target_ast_rate),
        float(target_obpm),
        float(target_age),
    ]

    # Build feature matrix for shrunk-Mahalanobis distance. Falls back to a
    # weighted-Euclidean distance if covariance is singular (small/uniform pools)
    # — same auto-fallback pattern as similarity_v3 below 3*n_features samples.
    matrix = [_vector(c) for c in candidates]
    inverse = None
    try:
        cov = covariance_matrix(matrix)
        shrunk = shrunk_covariance(cov, SHRINKAGE)
        inverse = invert_matrix(shrunk)
    except Exception:
        inverse = None

    scored: List[Tuple[float, RoleExpansionObservation]] = []
    if inverse is not None:
        for obs in candidates:
            try:
                dist = mahalanobis_distance(target_vec, _vector(obs), inverse)
            except Exception:
                continue
            scored.append((dist, obs))
    else:
        # Weighted-Euclidean fallback. Weights normalize feature scales so a
        # 1-unit difference in usg_delta (0.10) doesn't dominate a 5-unit age gap.
        weights = (10.0, 10.0, 0.5, 1.0, 0.2)  # usg, ts, ast_rate, obpm, age
        for obs in candidates:
            vec = _vector(obs)
            sq = sum(((target_vec[i] - vec[i]) * weights[i]) ** 2 for i in range(5))
            scored.append((sq ** 0.5, obs))

    scored.sort(key=lambda pair: pair[0])
    neighbors = [obs for _, obs in scored[:K_NEIGHBORS]]
    if len(neighbors) < MIN_NEIGHBORS_FOR_RESULT:
        return None

    deltas = sorted(n.ts_delta for n in neighbors)
    mean_uplift = mean(deltas)
    band_lo = _percentile(deltas, 25)
    band_hi = _percentile(deltas, 75)
    confidence = _confidence_band(len(neighbors))

    # Top-3 closest neighbors for the audit panel.
    top_examples: List[OpportunityUpliftComparable] = []
    for obs in neighbors[:3]:
        player = db.query(Player).filter_by(id=obs.player_id).first()
        top_examples.append(
            OpportunityUpliftComparable(
                player_name=player.full_name if player else f"id={obs.player_id}",
                from_season=obs.from_season,
                to_season=obs.to_season,
                usg_delta=obs.usg_delta,
                ts_delta=obs.ts_delta,
            )
        )

    return OpportunityUplift(
        mean_uplift=round(mean_uplift, 4),
        uplift_band_lower=round(band_lo, 4),
        uplift_band_upper=round(band_hi, 4),
        neighbor_count=len(neighbors),
        evidence_confidence=confidence,
        comparable_examples=top_examples,
    )
