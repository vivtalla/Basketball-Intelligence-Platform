"""Era-adjusted peer-comp engine for the CF3 Legacy view.

Reuses the existing ``similarity_service`` infrastructure but anchors
the comparison to the player's *career-aggregate* line rather than a
specific season — which is what makes a HOF-style cohort sensible. We
still use per-season z-score normalization to remove era bias, then
average each player's per-season z-vectors weighted by GP into a
single career z-vector before computing distance.

This keeps the pacing-and-baseline machinery proven by Sprint 67's
similarity_v3 while answering the qualitatively different question
"who in NBA history played a similar career to this player".
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, SeasonStat
from models.career_legacy import EraPeer
from services.similarity_service import (
    MIN_GP,
    SIMILARITY_STATS,
    STAT_KEYS,
    _distance_to_similarity,
    _euclidean,
    _season_norms,
)


# Minimum number of qualifying seasons to be eligible as a peer. This
# stops short single-season cameos from dominating top-N when they
# happen to align on a few stats.
PEER_MIN_SEASONS = 3


def _qualified_rows_career(db: Session) -> List[SeasonStat]:
    """Same MIN_GP gate as similarity_service but kept locally so we can
    extend the peer pool gate independently if needed."""
    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.gp >= MIN_GP,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    return [r for r in rows if all(getattr(r, k, None) is not None for k in STAT_KEYS)]


def _career_z_vector(
    rows: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
) -> Optional[List[float]]:
    """Average a player's per-season weighted z-vectors, weighted by GP.

    Returns None if the player has no qualifying season rows.
    """
    if not rows:
        return None
    total_gp = 0.0
    accum = [0.0] * len(SIMILARITY_STATS)
    for row in rows:
        season_norms = norms.get(row.season)
        if not season_norms:
            continue
        gp = float(row.gp or 0)
        if gp <= 0:
            continue
        season_vec: List[float] = []
        ok = True
        for key, weight in SIMILARITY_STATS:
            stat_norm = season_norms.get(key)
            val = getattr(row, key, None)
            if stat_norm is None or val is None:
                ok = False
                break
            std = stat_norm["std"] or 1.0
            season_vec.append(((float(val) - stat_norm["mean"]) / std) * weight)
        if not ok:
            continue
        for i, v in enumerate(season_vec):
            accum[i] += v * gp
        total_gp += gp
    if total_gp <= 0:
        return None
    return [v / total_gp for v in accum]


def _dominant_dimension(
    target_vec: List[float],
    peer_vec: List[float],
) -> Tuple[str, str]:
    """Find which similarity dimension drives the comp + emit a label.

    The "dominant dimension" is the SIMILARITY_STATS axis on which both
    vectors are large in absolute value (i.e. both above the league
    average) AND closest to each other. We return a short chip label
    describing it.
    """
    labels: Dict[str, str] = {
        "pts_pg": "similar volume scorer",
        "reb_pg": "similar rebounding role",
        "ast_pg": "similar playmaking role",
        "stl_pg": "similar perimeter defender",
        "blk_pg": "similar rim protection",
        "tov_pg": "similar ball security",
        "ts_pct": "similar shooting profile",
        "usg_pct": "similar usage profile",
        "per": "similar overall production",
    }
    best_key = "pts_pg"
    best_score = -1.0
    for i, (key, _) in enumerate(SIMILARITY_STATS):
        # Both player z-scores must be on the same side of league avg
        # before we can call the dimension a "shared strength".
        if target_vec[i] * peer_vec[i] <= 0:
            continue
        magnitude = min(abs(target_vec[i]), abs(peer_vec[i]))
        closeness = 1.0 / (1.0 + abs(target_vec[i] - peer_vec[i]))
        score = magnitude * closeness
        if score > best_score:
            best_score = score
            best_key = key
    return best_key, labels.get(best_key, "similar overall game")


def find_era_peers(db: Session, player_id: int, n: int = 8) -> List[EraPeer]:
    """Return up to N era-adjusted peers across all NBA history.

    Implementation:
      1. Gather all qualified season rows from `season_stats`.
      2. Compute per-season norms (mean+std) for each stat — same as
         similarity_service.
      3. For each player, average their per-season z-vectors weighted by
         GP into a single career z-vector.
      4. Distance from the target's career vector to every other
         player's career vector is converted to a 0..100 similarity
         score. Top-N (excluding the target) are returned.
    """
    all_rows = _qualified_rows_career(db)
    if not all_rows:
        return []
    norms = _season_norms(all_rows)

    by_player: Dict[int, List[SeasonStat]] = defaultdict(list)
    for row in all_rows:
        by_player[row.player_id].append(row)

    target_rows = by_player.get(player_id, [])
    target_vec = _career_z_vector(target_rows, norms)
    if target_vec is None:
        return []

    # Pre-compute all peer career vectors.
    scored: List[Tuple[float, int, List[float], int]] = []
    for pid, rows in by_player.items():
        if pid == player_id:
            continue
        if len(rows) < PEER_MIN_SEASONS:
            continue
        vec = _career_z_vector(rows, norms)
        if vec is None:
            continue
        dist = _euclidean(target_vec, vec)
        scored.append((dist, pid, vec, len(rows)))

    scored.sort(key=lambda x: x[0])
    top = scored[: max(1, min(n, 10))]

    if not top:
        return []

    player_ids = [pid for _, pid, _, _ in top]
    players_lookup = {
        p.id: p
        for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }

    out: List[EraPeer] = []
    for dist, pid, vec, season_count in top:
        player = players_lookup.get(pid)
        _, basis_label = _dominant_dimension(target_vec, vec)
        out.append(
            EraPeer(
                player_id=pid,
                player_name=player.full_name if player else str(pid),
                headshot_url=player.headshot_url if player else None,
                seasons_played=season_count,
                similarity_score=_distance_to_similarity(dist),
                comp_basis=basis_label,
            )
        )
    return out
