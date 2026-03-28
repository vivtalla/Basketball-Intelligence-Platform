"""Player similarity engine.

Finds the most statistically similar player-seasons to a given player-season
using z-score normalization (within each season) followed by Euclidean distance.

Normalization per season removes era bias — a player is compared to how they
ranked among their peers, not against raw numbers from a different decade.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from db.models import Player, SeasonStat

# Stats used for similarity matching. All must be non-null to include a row.
# Weights let us emphasize role-defining stats over noisy ones.
SIMILARITY_STATS: list[tuple[str, float]] = [
    ("pts_pg",  1.5),   # scoring volume — high signal for role
    ("reb_pg",  1.5),   # rebounding role
    ("ast_pg",  1.5),   # playmaking role
    ("stl_pg",  1.0),   # defensive activity
    ("blk_pg",  1.0),   # rim protection
    ("tov_pg",  0.8),   # ball security
    ("ts_pct",  1.2),   # efficiency
    ("usg_pct", 1.2),   # usage/role
    ("per",     1.0),   # overall value
]

STAT_KEYS = [s for s, _ in SIMILARITY_STATS]
STAT_WEIGHTS = [w for _, w in SIMILARITY_STATS]
MIN_GP = 20  # minimum games to be included in similarity pool


def _get_all_qualified_seasons(db: Session) -> list[SeasonStat]:
    """Pull all season rows with enough games and required stats populated."""
    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.gp >= MIN_GP,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    # Keep only rows where all similarity stats are present
    return [
        r for r in rows
        if all(getattr(r, k, None) is not None for k in STAT_KEYS)
    ]


def _season_norms(rows: list[SeasonStat]) -> dict[str, dict[str, float]]:
    """Compute per-season mean and std for each stat key.

    Returns: { season: { stat_key: {"mean": float, "std": float} } }
    """
    by_season: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        for key in STAT_KEYS:
            val = getattr(row, key)
            if val is not None:
                by_season[row.season][key].append(float(val))

    norms: dict[str, dict[str, dict[str, float]]] = {}
    for season, stat_vals in by_season.items():
        norms[season] = {}
        for key, vals in stat_vals.items():
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / max(len(vals) - 1, 1)
            std = math.sqrt(variance) if variance > 0 else 1.0
            norms[season][key] = {"mean": mean, "std": std}

    return norms


def _z_vector(row: SeasonStat, norms: dict[str, dict[str, float]]) -> Optional[list[float]]:
    """Return the weighted z-score vector for a season stat row, or None if missing norms."""
    season_norms = norms.get(row.season)
    if not season_norms:
        return None
    z = []
    for key, weight in SIMILARITY_STATS:
        stat_norm = season_norms.get(key)
        val = getattr(row, key, None)
        if stat_norm is None or val is None:
            return None  # missing stat — skip this row
        z_val = (float(val) - stat_norm["mean"]) / stat_norm["std"]
        z.append(z_val * weight)
    return z


def _euclidean(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _distance_to_similarity(dist: float) -> float:
    """Convert Euclidean distance to a 0–100 similarity score."""
    # Empirically, most distances fall in 0–8 range; score decays smoothly.
    return round(100.0 / (1.0 + dist), 1)


def find_similar_players(
    db: Session,
    player_id: int,
    season: str,
    n: int = 8,
    cross_era: bool = True,
) -> list[dict]:
    """Return the top-N most similar player-seasons to player_id in the given season.

    Args:
        cross_era: if True, compare across all seasons (era-adjusted via z-scores).
                   if False, restrict candidates to the same season only.
    Returns list of dicts with player info, similarity score, and key stats.
    """
    all_rows = _get_all_qualified_seasons(db)
    norms = _season_norms(all_rows)

    # Find target row
    target_row = next(
        (r for r in all_rows if r.player_id == player_id and r.season == season),
        None,
    )
    if target_row is None:
        return []

    target_vec = _z_vector(target_row, norms)
    if target_vec is None:
        return []

    # Build candidate pool
    candidates = [
        r for r in all_rows
        if not (r.player_id == player_id and r.season == season)  # exclude self
        and (cross_era or r.season == season)
    ]

    # Score each candidate
    scored: list[tuple[float, SeasonStat]] = []
    for row in candidates:
        vec = _z_vector(row, norms)
        if vec is None:
            continue
        dist = _euclidean(target_vec, vec)
        scored.append((dist, row))

    scored.sort(key=lambda x: x[0])
    top = scored[:n]

    # Resolve player names
    player_ids = {row.player_id for _, row in top}
    players = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}

    results = []
    for dist, row in top:
        player = players.get(row.player_id)
        results.append({
            "player_id": row.player_id,
            "player_name": player.full_name if player else str(row.player_id),
            "headshot_url": player.headshot_url if player else None,
            "season": row.season,
            "team_abbreviation": row.team_abbreviation,
            "similarity_score": _distance_to_similarity(dist),
            "gp": row.gp,
            # Key stats for display
            "pts_pg": row.pts_pg,
            "reb_pg": row.reb_pg,
            "ast_pg": row.ast_pg,
            "ts_pct": row.ts_pct,
            "usg_pct": row.usg_pct,
            "per": row.per,
        })

    return results
