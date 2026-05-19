"""Sprint 104 (Stream B) — algorithmic strengths/weaknesses + archetype synthesis.

Reads the prospect's most-recent ``DraftProspectStat`` row, z-scores
each feature against the pool of other prospects in the same
``draft_year`` and same position bucket (G/F/C), and emits:

  - Top-2 features where z >= +0.7 → strengths.
  - Bottom-2 features where z <= -0.7 → weaknesses.
  - Nearest-centroid archetype label from a fixed 6-archetype palette.

The whole computation is on-demand and stateless — no caching, no
schema changes. If the pool is too small (<5 peers) the result is
flagged ``insufficient_pool=True`` so the UI can render a caveat.

This service exists because the prospect-detail page has 15 sections
of numeric stats but no readable "what's this prospect's game"
synthesis. The Sprint 78 lesson — fabricated text leaks into prod —
ruled out AI-generated scouting blurbs; algorithmic derivation from
existing real stats is the slop-free alternative.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import DraftProspect, DraftProspectStat
from models.draft import ProspectFeatureNote, ProspectProfile

logger = logging.getLogger(__name__)

METHODOLOGY_VERSION = "synthesis_v1"
Z_THRESHOLD = 0.7
MIN_POOL_SIZE = 5
MAX_HIGHLIGHTS = 2

# Feature columns on DraftProspectStat we compare across the pool.
_FEATURE_COLUMNS: Tuple[str, ...] = (
    "pts_pg", "ts_pct", "reb_pg", "ast_pg", "fg3_pct", "usg_pct",
)

# Human-readable labels keyed by (feature, direction).
_LABELS: Dict[Tuple[str, str], str] = {
    ("pts_pg", "high"): "Plus scoring volume",
    ("pts_pg", "low"): "Limited scoring volume",
    ("ts_pct", "high"): "Elite shot efficiency",
    ("ts_pct", "low"): "Inefficient scoring",
    ("reb_pg", "high"): "Strong rebounding",
    ("reb_pg", "low"): "Limited rebounding",
    ("ast_pg", "high"): "Plus playmaking",
    ("ast_pg", "low"): "Limited playmaking",
    ("fg3_pct", "high"): "Reliable three-point shooting",
    ("fg3_pct", "low"): "Three-point shooting question",
    ("usg_pct", "high"): "Heavy on-ball usage",
    ("usg_pct", "low"): "Off-ball role player",
}

# Position bucketing (mirrors comp_service_v2._POSITION_BUCKETS).
_POSITION_BUCKETS: Dict[str, str] = {
    "PG": "G", "SG": "G", "G": "G",
    "SF": "F", "PF": "F", "F": "F",
    "C": "C",
}

# Archetype centroids in feature z-space. Each value is the z-score the
# archetype "should" have on that feature. Distance is Euclidean across
# the feature list.
_ARCHETYPES: Dict[str, Dict[str, float]] = {
    "Lead Guard":        {"pts_pg": 0.5,  "ts_pct": 0.0,  "reb_pg": -0.8, "ast_pg": 1.2,  "fg3_pct": 0.3,  "usg_pct": 0.8},
    "Wing Scorer":       {"pts_pg": 1.0,  "ts_pct": 0.0,  "reb_pg": -0.3, "ast_pg": -0.3, "fg3_pct": 0.4,  "usg_pct": 0.9},
    "Combo Wing":        {"pts_pg": 0.3,  "ts_pct": 0.8,  "reb_pg": 0.2,  "ast_pg": 0.2,  "fg3_pct": 1.0,  "usg_pct": 0.0},
    "Stretch Big":       {"pts_pg": 0.2,  "ts_pct": 0.5,  "reb_pg": 1.0,  "ast_pg": -0.5, "fg3_pct": 1.0,  "usg_pct": 0.0},
    "Rim Big":           {"pts_pg": 0.3,  "ts_pct": 1.0,  "reb_pg": 1.2,  "ast_pg": -0.7, "fg3_pct": -1.0, "usg_pct": 0.3},
    "Defensive Anchor":  {"pts_pg": -0.5, "ts_pct": 0.0,  "reb_pg": 0.8,  "ast_pg": -0.6, "fg3_pct": -0.5, "usg_pct": -0.5},
}


def _position_bucket(pos: Optional[str]) -> Optional[str]:
    if not pos:
        return None
    return _POSITION_BUCKETS.get(pos.strip().upper())


def _latest_stat_row(db: Session, prospect_id: int) -> Optional[DraftProspectStat]:
    return (
        db.query(DraftProspectStat)
        .filter(DraftProspectStat.prospect_id == prospect_id)
        .order_by(DraftProspectStat.season.desc())
        .first()
    )


def _features_from_stat(stat: DraftProspectStat) -> Dict[str, float]:
    return {
        col: float(getattr(stat, col) or 0.0)
        for col in _FEATURE_COLUMNS
    }


def _pool_stats(
    db: Session,
    draft_year: int,
    target_bucket: Optional[str],
    exclude_prospect_id: int,
) -> Tuple[List[Dict[str, float]], int, Optional[str]]:
    """Return (pool_features, pool_size, pool_bucket).

    Pool is same-draft-year prospects in the same position bucket. Falls
    back to all same-draft-year prospects if the bucket pool is too
    small.
    """
    candidates = (
        db.query(DraftProspect)
        .filter(DraftProspect.draft_year == draft_year)
        .filter(DraftProspect.id != exclude_prospect_id)
        .all()
    )

    bucket_features: List[Dict[str, float]] = []
    all_features: List[Dict[str, float]] = []
    for cand in candidates:
        stat = _latest_stat_row(db, cand.id)
        if stat is None:
            continue
        feats = _features_from_stat(stat)
        all_features.append(feats)
        if target_bucket is not None and _position_bucket(cand.primary_position) == target_bucket:
            bucket_features.append(feats)

    if target_bucket is not None and len(bucket_features) >= MIN_POOL_SIZE:
        return bucket_features, len(bucket_features), target_bucket
    # Fallback to year pool (across positions). Distance interpretation
    # loses some signal but the synthesis still works.
    return all_features, len(all_features), None


def _zscore(value: float, pool_values: List[float]) -> float:
    if len(pool_values) < 2:
        return 0.0
    mean = sum(pool_values) / len(pool_values)
    var = sum((v - mean) ** 2 for v in pool_values) / (len(pool_values) - 1)
    std = var ** 0.5
    if std < 1e-6:
        return 0.0
    return (value - mean) / std


def _nearest_archetype(target_z: Dict[str, float]) -> Tuple[str, float]:
    best_label = "Unclassified"
    best_distance = float("inf")
    for label, centroid in _ARCHETYPES.items():
        d = 0.0
        for feature, c_z in centroid.items():
            d += (target_z.get(feature, 0.0) - c_z) ** 2
        d = d ** 0.5
        if d < best_distance:
            best_distance = d
            best_label = label
    return best_label, round(best_distance, 3)


def synthesize_profile(db: Session, prospect: DraftProspect) -> Optional[ProspectProfile]:
    """Algorithmic synthesis. Returns None if the prospect has no stat row."""
    stat = _latest_stat_row(db, prospect.id)
    if stat is None:
        return None

    target_features = _features_from_stat(stat)
    target_bucket = _position_bucket(prospect.primary_position)

    pool_features, pool_size, pool_bucket = _pool_stats(
        db, prospect.draft_year, target_bucket, prospect.id
    )

    if pool_size < MIN_POOL_SIZE:
        return ProspectProfile(
            archetype_label="Unclassified",
            archetype_distance=0.0,
            strengths=[],
            weaknesses=[],
            pool_size=pool_size,
            pool_bucket=pool_bucket,
            insufficient_pool=True,
            methodology_version=METHODOLOGY_VERSION,
        )

    target_z: Dict[str, float] = {}
    for col in _FEATURE_COLUMNS:
        pool_values = [f[col] for f in pool_features]
        target_z[col] = _zscore(target_features[col], pool_values)

    # Rank features by z. Top quartile (z >= threshold) → strengths;
    # bottom quartile (z <= -threshold) → weaknesses.
    ranked = sorted(target_z.items(), key=lambda kv: kv[1], reverse=True)
    strengths: List[ProspectFeatureNote] = []
    weaknesses: List[ProspectFeatureNote] = []

    for feature, z in ranked:
        if z >= Z_THRESHOLD and len(strengths) < MAX_HIGHLIGHTS:
            label = _LABELS.get((feature, "high"), feature)
            strengths.append(ProspectFeatureNote(feature_key=feature, label=label, z_score=round(z, 3)))

    for feature, z in reversed(ranked):
        if z <= -Z_THRESHOLD and len(weaknesses) < MAX_HIGHLIGHTS:
            label = _LABELS.get((feature, "low"), feature)
            weaknesses.append(ProspectFeatureNote(feature_key=feature, label=label, z_score=round(z, 3)))

    archetype_label, archetype_distance = _nearest_archetype(target_z)

    return ProspectProfile(
        archetype_label=archetype_label,
        archetype_distance=archetype_distance,
        strengths=strengths,
        weaknesses=weaknesses,
        pool_size=pool_size,
        pool_bucket=pool_bucket,
        insufficient_pool=False,
        methodology_version=METHODOLOGY_VERSION,
    )
