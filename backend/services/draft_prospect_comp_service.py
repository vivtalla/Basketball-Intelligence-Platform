"""Sprint 78 / FO3 — NBA comp matching for draft prospects.

Approach (intentionally simple — no covariance, no MLE):

1. Build the prospect's NBA-translated stat vector from
   ``draft_translation_service.translate_prospect_to_nba``. We pull the
   same six box dimensions the similarity service uses (pts/reb/ast/ts/usg
   plus tov), expressed on an NBA per-100 scale.
2. Pull the most-recent regular-season frame from ``season_stats`` (uses
   ``similarity_service`` season-norm helpers) and compute the same z-score
   feature vector for every NBA player-season that qualifies.
3. Project the prospect's translated line into the same z-score space using
   the NBA pool's mean / std. Per-100 prospect numbers go in directly —
   the NBA pool is already on a per-game basis, but at NBA pace per-game
   ≈ per-100 / (100/PACE_NBA) ≈ per-game; we therefore convert the NBA pool
   to per-100 first by multiplying by 100/PACE_NBA, with PACE_NBA pulled
   from the league average. Approximating PACE_NBA = 100 keeps the
   transform a no-op for the NBA pool, which is exactly the point — the
   prospect's translated per-100 line is already on the same scale as the
   NBA pool's per-100 baseline.
4. Score by Euclidean distance, take top-K, and attach the archetype
   label via ``classify_many`` so each comp comes with a one-word style
   tag.
5. Build a short rationale string — "Big-bodied wing with rebounding
   load" — by picking the two strongest matched z-features and mapping
   them through the existing ``TEAM_FIT_FEATURE_LABELS`` dictionary.

This is intentionally **not** the full Mahalanobis path from
``similarity_v3``. The prospect doesn't have an opponent-adjusted
covariance to invert; a cheap, transparent Euclidean fit gives 5 pickable
veterans without overstating the precision of the projection. When
real combine + tracking measurements come online next sprint, swap in
the v3 distance under the hood without changing the response shape.
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import DraftProspect, Player, SeasonStat
from models.draft import NbaComp
from services.draft_translation_service import (
    NBA_PACE,
    translate_prospect_to_nba,
)
from services.player_archetype_service import classify_many

logger = logging.getLogger(__name__)


# Feature set + weights tuned for the prospect ➜ NBA comp use case.
# Same six-stat box footprint similarity_service uses, minus PER (which
# isn't available for college rows). Scoring volume + role weights (usage,
# playmaking) get the heaviest pull because those map cleanest from the
# pre-NBA league.
_FEATURES: List[Tuple[str, float]] = [
    ("pts_pg",  1.5),
    ("reb_pg",  1.3),
    ("ast_pg",  1.3),
    ("stl_pg",  0.7),
    ("blk_pg",  0.7),
    ("tov_pg",  0.7),
    ("ts_pct",  1.2),
    ("usg_pct", 1.2),
]

_FEATURE_LABELS: Dict[str, str] = {
    "pts_pg": "scoring volume",
    "reb_pg": "rebounding load",
    "ast_pg": "playmaking",
    "stl_pg": "perimeter activity",
    "blk_pg": "rim protection",
    "tov_pg": "ball security",
    "ts_pct": "shooting efficiency",
    "usg_pct": "usage rate",
}

_MIN_GP = 30  # NBA pool floor — at least half a season


def _latest_season_in_db(db: Session) -> Optional[str]:
    row = (
        db.query(SeasonStat.season)
        .filter(SeasonStat.is_playoff == False)  # noqa: E712
        .order_by(SeasonStat.season.desc())
        .first()
    )
    return row[0] if row else None


def _qualified_nba_rows(db: Session, season: str) -> List[SeasonStat]:
    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == False,  # noqa: E712
            SeasonStat.gp >= _MIN_GP,
        )
        .all()
    )
    return [
        r for r in rows
        if all(getattr(r, k, None) is not None for k, _ in _FEATURES)
    ]


def _per100(val: float, pace: float = NBA_PACE) -> float:
    """Convert NBA per-game to per-100. Pace ≈ 100 in modern NBA, so this is near identity."""
    if pace <= 0:
        return val
    return val * (100.0 / pace)


def _pool_norms(rows: List[SeasonStat]) -> Dict[str, Dict[str, float]]:
    """Per-100 mean/std for each feature on the NBA pool."""
    cols: Dict[str, List[float]] = defaultdict(list)
    for row in rows:
        for key, _ in _FEATURES:
            v = getattr(row, key, None)
            if v is None:
                continue
            # Counting stats translated to per-100; rates kept as-is.
            cols[key].append(_per100(float(v)) if key.endswith("_pg") else float(v))
    out: Dict[str, Dict[str, float]] = {}
    for key, vals in cols.items():
        if not vals:
            continue
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / max(len(vals) - 1, 1)
        std = math.sqrt(var) or 1.0
        out[key] = {"mean": mean, "std": std}
    return out


def _z_vector_from_nba_row(
    row: SeasonStat,
    norms: Dict[str, Dict[str, float]],
    active_keys: List[str],
) -> Optional[List[float]]:
    z: List[float] = []
    for key, weight in _FEATURES:
        if key not in active_keys:
            continue
        nrm = norms.get(key)
        v = getattr(row, key, None)
        if nrm is None or v is None:
            return None
        sample = _per100(float(v)) if key.endswith("_pg") else float(v)
        z.append(((sample - nrm["mean"]) / nrm["std"]) * weight)
    return z


def _z_vector_from_translation(
    translation_values: Dict[str, Optional[float]],
    norms: Dict[str, Dict[str, float]],
    active_keys: List[str],
) -> Optional[List[float]]:
    z: List[float] = []
    for key, weight in _FEATURES:
        if key not in active_keys:
            continue
        nrm = norms.get(key)
        v = translation_values.get(key)
        if nrm is None or v is None:
            return None
        z.append(((float(v) - nrm["mean"]) / nrm["std"]) * weight)
    return z


def _euclidean(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _similarity_score(dist: float) -> float:
    return round(100.0 / (1.0 + dist), 1)


def _rationale(target: List[float], comp: List[float], active_keys: List[str]) -> str:
    """Pick the two features where the comp's z-vector is closest to the target's
    *and* both are noticeably above league average. Reads like "rim protection +
    rebounding load"."""
    diffs = [(abs(t - c), key, c) for key, t, c in zip(active_keys, target, comp)]
    diffs.sort(key=lambda x: (x[0], -x[2]))
    matched = [d for d in diffs if d[2] >= 0.0][:2] or diffs[:2]
    chips = [_FEATURE_LABELS.get(k, k) for _, k, _ in matched]
    if len(chips) >= 2:
        return f"{chips[0].capitalize()} + {chips[1]}"
    if chips:
        return chips[0].capitalize()
    return "Statistical fit"


def find_nba_comps(
    db: Session,
    prospect_id: int,
    k: int = 5,
    season: Optional[str] = None,
) -> List[NbaComp]:
    """Find the K most-similar NBA player-seasons to a prospect.

    `season` defaults to the latest season present in `season_stats`.
    """
    prospect: Optional[DraftProspect] = db.query(DraftProspect).filter(
        DraftProspect.id == prospect_id
    ).one_or_none()
    if prospect is None:
        return []

    translation = translate_prospect_to_nba(db, prospect_id)
    if translation is None:
        return []

    season = season or _latest_season_in_db(db)
    if not season:
        return []

    pool = _qualified_nba_rows(db, season)
    if len(pool) < k:
        return []

    norms = _pool_norms(pool)
    if not norms:
        return []

    target_values: Dict[str, Optional[float]] = {
        "pts_pg":  translation.projected_pts_per100,
        "reb_pg":  translation.projected_reb_per100,
        "ast_pg":  translation.projected_ast_per100,
        "stl_pg":  translation.projected_stl_per100,
        "blk_pg":  translation.projected_blk_per100,
        "tov_pg":  translation.projected_tov_per100,
        "ts_pct":  translation.projected_ts_pct,
        "usg_pct": translation.projected_usg_pct,
    }
    # Only score on features the prospect actually has — seed CSVs without
    # combine-quality stl/blk/tov shouldn't tank the whole match.
    active_keys: List[str] = [k for k, _ in _FEATURES if target_values.get(k) is not None]
    if len(active_keys) < 4:
        return []

    target_vec = _z_vector_from_translation(target_values, norms, active_keys)
    if target_vec is None:
        return []

    scored: List[Tuple[float, SeasonStat, List[float]]] = []
    for row in pool:
        vec = _z_vector_from_nba_row(row, norms, active_keys)
        if vec is None:
            continue
        scored.append((_euclidean(target_vec, vec), row, vec))

    scored.sort(key=lambda x: x[0])
    top = scored[:k]

    player_ids = [row.player_id for _, row, _ in top]
    players = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}
    archetypes = classify_many(db, player_ids, season, season_type="Regular Season")

    comps: List[NbaComp] = []
    for dist, row, vec in top:
        player = players.get(row.player_id)
        archetype = archetypes.get(row.player_id)
        comps.append(NbaComp(
            player_id=row.player_id,
            player_name=player.full_name if player else f"Player {row.player_id}",
            headshot_url=player.headshot_url if player else None,
            season=row.season,
            team_abbreviation=row.team_abbreviation,
            similarity_score=_similarity_score(dist),
            archetype_label=archetype.label if archetype else None,
            rationale=_rationale(target_vec, vec, active_keys),
            pts_pg=row.pts_pg,
            reb_pg=row.reb_pg,
            ast_pg=row.ast_pg,
            ts_pct=row.ts_pct,
            usg_pct=row.usg_pct,
        ))

    return comps
