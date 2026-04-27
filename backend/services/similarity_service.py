"""Player similarity engine.

Finds the most statistically similar player-seasons to a given player-season
using z-score normalization (within each season) followed by Euclidean distance.

Normalization per season removes era bias — a player is compared to how they
ranked among their peers, not against raw numbers from a different decade.

Sprint 67 (B2) adds:
- role-aware V2 distance with 4 extra features (par3, ftr, stl/36, blk/36)
- `mode` parameter selecting the candidate pool: season|age|team_fit
- archetype label attached to every comp via batch classify
The legacy `find_similar_players(cross_era=...)` signature is preserved for
existing callers (the /api/similarity/{player_id} default response).
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Dict, List, Literal, Optional, Tuple

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


# ---------------------------------------------------------------------------
# Sprint 67 (B2) — role-aware similarity with archetype attachment
# ---------------------------------------------------------------------------

SimilarityMode = Literal["season", "age", "team_fit"]

# Extended feature set: the original 9 role-defining box stats plus 4 dimensions
# that the Sprint 67 archetype engine uses (perimeter diet, foul drawing, and
# per-36 defensive activity). These push "Nic Claxton vs Clint Capela" apart
# from "Nic Claxton vs Draymond Green" in ways raw pts/reb/ast don't.
SIMILARITY_STATS_V2: List[Tuple[str, float]] = [
    *SIMILARITY_STATS,
    ("par3", 1.0),   # FG3A / FGA
    ("ftr",  1.0),   # FTA / FGA
    ("stl_pg", 0.6),
    ("blk_pg", 0.6),
]
STAT_KEYS_V2 = [s for s, _ in SIMILARITY_STATS_V2]

TEAM_FIT_FEATURE_LABELS: Dict[str, str] = {
    "pts_pg": "Scoring",
    "reb_pg": "Rebounding",
    "ast_pg": "Playmaking",
    "stl_pg": "Defensive activity",
    "blk_pg": "Rim protection",
    "tov_pg": "Ball security",
    "ts_pct": "Efficiency",
    "usg_pct": "Usage",
    "per": "Overall production",
    "par3": "Spacing",
    "ftr": "Rim pressure",
}

# Age-mode window (season start year +/- this many years).
AGE_WINDOW = 1


def _qualified_rows_v2(db: Session) -> List[SeasonStat]:
    """Same MIN_GP + regular-season filter as the legacy path but against the V2 feature list."""
    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.gp >= MIN_GP,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    return [r for r in rows if all(getattr(r, k, None) is not None for k in STAT_KEYS_V2)]


def _season_norms_v2(rows: List[SeasonStat]) -> Dict[str, Dict[str, Dict[str, float]]]:
    by_season: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        for key in STAT_KEYS_V2:
            val = getattr(row, key, None)
            if val is not None:
                by_season[row.season][key].append(float(val))
    norms: Dict[str, Dict[str, Dict[str, float]]] = {}
    for season, stat_vals in by_season.items():
        norms[season] = {}
        for key, vals in stat_vals.items():
            if len(vals) < 2:
                norms[season][key] = {"mean": vals[0] if vals else 0.0, "std": 1.0}
                continue
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)
            std = math.sqrt(variance) if variance > 0 else 1.0
            norms[season][key] = {"mean": mean, "std": std}
    return norms


def _z_vector_v2(row: SeasonStat, norms: Dict[str, Dict[str, Dict[str, float]]]) -> Optional[List[float]]:
    season_norms = norms.get(row.season)
    if not season_norms:
        return None
    z: List[float] = []
    for key, weight in SIMILARITY_STATS_V2:
        stat_norm = season_norms.get(key)
        val = getattr(row, key, None)
        if stat_norm is None or val is None:
            return None
        std = stat_norm["std"] or 1.0
        z.append(((float(val) - stat_norm["mean"]) / std) * weight)
    return z


def _player_birth_lookup(db: Session, player_ids: List[int]) -> Dict[int, Optional[str]]:
    if not player_ids:
        return {}
    return {
        p.id: p.birth_date
        for p in db.query(Player).filter(Player.id.in_(player_ids)).all()
    }


def _build_candidate_pool(
    all_rows: List[SeasonStat],
    target_row: SeasonStat,
    mode: SimilarityMode,
    db: Session,
) -> List[SeasonStat]:
    """Filter the qualified pool down to the candidates a given mode cares about."""
    # Never compare a player to themselves in that same season.
    def _not_self(r: SeasonStat) -> bool:
        return not (r.player_id == target_row.player_id and r.season == target_row.season)

    if mode == "season":
        return [r for r in all_rows if _not_self(r) and r.season == target_row.season]

    if mode == "age":
        # Import locally to avoid module-load cycle with player_archetype_service.
        from services.player_archetype_service import parse_age_as_of_season

        target_birth = _player_birth_lookup(db, [target_row.player_id]).get(target_row.player_id)
        target_age = parse_age_as_of_season(target_birth, target_row.season)
        if target_age is None:
            return []

        candidate_ids = list({r.player_id for r in all_rows})
        births = _player_birth_lookup(db, candidate_ids)

        out: List[SeasonStat] = []
        for r in all_rows:
            # In age mode, exclude the subject player across all seasons — showing
            # "you at 23" next to "you at 25" isn't a comp, it's trivia.
            if r.player_id == target_row.player_id:
                continue
            age = parse_age_as_of_season(births.get(r.player_id), r.season)
            if age is None:
                continue
            if abs(age - target_age) <= AGE_WINDOW:
                out.append(r)
        return out

    if mode == "team_fit":
        # Same-season league-wide candidate pool, subject excluded. The
        # teammate-duplicate penalty is applied at the distance layer, not the
        # pool layer — candidates remain the same as season-mode, what changes
        # is how distance weights shift per feature for THIS subject.
        return [r for r in all_rows if _not_self(r) and r.season == target_row.season]

    raise ValueError(f"unknown similarity mode: {mode!r}")


def _select_team_fit_subject_row(
    all_rows: List[SeasonStat],
    player_id: int,
    season: str,
) -> Optional[SeasonStat]:
    player_rows = [
        r for r in all_rows
        if r.player_id == player_id and r.season == season
    ]
    non_tot = [r for r in player_rows if (r.team_abbreviation or "").upper() != "TOT"]
    if non_tot:
        non_tot.sort(key=lambda r: (float(r.min_pg or 0.0), int(r.gp or 0)), reverse=True)
        return non_tot[0]
    return player_rows[0] if player_rows else None


# --- Team-fit teammate-duplicate penalty (spec §1.7) ------------------------

# Z-gap threshold below which we consider the subject "already covered" on a
# feature by a teammate. Per spec §1.7.
_TEAM_FIT_DUPLICATE_THRESHOLD = 0.5
# Weight multiplier applied to duplicated features so comps differentiating
# there contribute less to distance (team-fit-style complement ranking).
_TEAM_FIT_PENALTY = 0.4


def _raw_z(row: SeasonStat, norms: Dict[str, Dict[str, Dict[str, float]]]) -> Optional[Dict[str, float]]:
    """Return unweighted z-scores keyed by feature name, or None if any feature is missing."""
    season_norms = norms.get(row.season)
    if not season_norms:
        return None
    out: Dict[str, float] = {}
    for key, _weight in SIMILARITY_STATS_V2:
        stat_norm = season_norms.get(key)
        val = getattr(row, key, None)
        if stat_norm is None or val is None:
            return None
        std = stat_norm["std"] or 1.0
        out[key] = (float(val) - stat_norm["mean"]) / std
    return out


def _team_fit_weight_overrides(
    target_row: SeasonStat,
    all_rows: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
) -> Dict[str, float]:
    """For each similarity feature, return a multiplier that softens (×0.4) the
    feature's weight when the subject and a same-team teammate both project at
    similar z-scores — i.e. the team already covers that feature and comps who
    merely duplicate it shouldn't dominate the ranking.
    """
    subject_z = _raw_z(target_row, norms) or {}
    teammate_rows = [
        r for r in all_rows
        if r.season == target_row.season
        and r.team_abbreviation == target_row.team_abbreviation
        and r.player_id != target_row.player_id
    ]
    teammate_raw = [z for z in (_raw_z(r, norms) for r in teammate_rows) if z is not None]

    overrides: Dict[str, float] = {}
    for key, _weight in SIMILARITY_STATS_V2:
        subj_z = subject_z.get(key)
        if subj_z is None:
            overrides[key] = 1.0
            continue
        closest_gap = None
        for tm in teammate_raw:
            tm_z = tm.get(key)
            if tm_z is None:
                continue
            gap = abs(subj_z - tm_z)
            if closest_gap is None or gap < closest_gap:
                closest_gap = gap
        if closest_gap is not None and closest_gap < _TEAM_FIT_DUPLICATE_THRESHOLD:
            overrides[key] = _TEAM_FIT_PENALTY
        else:
            overrides[key] = 1.0
    return overrides


def _team_fit_overlap_context(
    db: Session,
    target_row: SeasonStat,
    all_rows: List[SeasonStat],
    norms: Dict[str, Dict[str, Dict[str, float]]],
) -> List[Dict[str, Any]]:
    """Return the visible explanation for Sprint 68's hidden Team-Fit penalty.

    The ranking code only needs per-feature weight multipliers, but the UI needs
    to know which teammate caused each multiplier. This mirrors
    _team_fit_weight_overrides while preserving the closest covering teammate.
    """
    subject_z = _raw_z(target_row, norms) or {}
    teammate_rows = [
        r for r in all_rows
        if r.season == target_row.season
        and r.team_abbreviation == target_row.team_abbreviation
        and r.player_id != target_row.player_id
    ]
    closest: Dict[str, Tuple[float, SeasonStat, float]] = {}
    for row in teammate_rows:
        teammate_z = _raw_z(row, norms)
        if teammate_z is None:
            continue
        for key, _weight in SIMILARITY_STATS_V2:
            subj = subject_z.get(key)
            tm = teammate_z.get(key)
            if subj is None or tm is None:
                continue
            gap = abs(subj - tm)
            if gap >= _TEAM_FIT_DUPLICATE_THRESHOLD:
                continue
            current = closest.get(key)
            if current is None or gap < current[0]:
                closest[key] = (gap, row, tm)

    teammate_ids = [row.player_id for _gap, row, _tm_z in closest.values()]
    players = {
        p.id: p for p in db.query(Player).filter(Player.id.in_(teammate_ids)).all()
    } if teammate_ids else {}

    flags: List[Dict[str, Any]] = []
    for key, (gap, row, teammate_z) in closest.items():
        player = players.get(row.player_id)
        flags.append({
            "feature_key": key,
            "label": TEAM_FIT_FEATURE_LABELS.get(key, key),
            "teammate_id": row.player_id,
            "teammate_name": player.full_name if player else str(row.player_id),
            "player_z": round(float(subject_z[key]), 3),
            "teammate_z": round(float(teammate_z), 3),
            "gap": round(float(gap), 3),
            "multiplier": _TEAM_FIT_PENALTY,
        })
    flags.sort(key=lambda item: (item["gap"], item["label"]))
    return flags


def build_team_fit_similarity_context(
    db: Session,
    player_id: int,
    season: str,
) -> Optional[Dict[str, Any]]:
    all_rows = _qualified_rows_v2(db)
    norms = _season_norms_v2(all_rows)
    target_row = _select_team_fit_subject_row(all_rows, player_id, season)
    if target_row is None:
        return None
    flags = _team_fit_overlap_context(db, target_row, all_rows, norms)
    team = target_row.team_abbreviation
    if flags:
        first = flags[0]
        summary = "Team-Fit ranking softens {0} because {1} already covers it.".format(
            first["label"].lower(),
            first["teammate_name"],
        )
    else:
        summary = "Team-Fit ranking found no same-team duplicate features to soften."
    return {
        "team_abbreviation": team,
        "overlap_flags": flags,
        "summary": summary,
    }


def _weighted_vec(
    raw: Dict[str, float],
    overrides: Optional[Dict[str, float]] = None,
) -> List[float]:
    """Apply the base SIMILARITY_STATS_V2 weights (and optional per-feature
    multipliers) to a raw z-score dict in canonical feature order.
    """
    out: List[float] = []
    for key, weight in SIMILARITY_STATS_V2:
        mult = (overrides or {}).get(key, 1.0)
        out.append(raw[key] * weight * mult)
    return out


def find_similar_players_with_archetype(
    db: Session,
    player_id: int,
    season: str,
    mode: SimilarityMode = "season",
    n: int = 8,
) -> List[dict]:
    """Sprint 67 (B2) role-aware similarity.

    Extends the legacy 9-feature Euclidean distance with 4 archetype-defining
    dimensions and attaches an archetype label to every returned comp. See
    specs/sprint-67-archetype-rules.md §1.7 for contract details.
    """
    all_rows = _qualified_rows_v2(db)
    norms = _season_norms_v2(all_rows)

    if mode == "team_fit":
        target_row = _select_team_fit_subject_row(all_rows, player_id, season)
    else:
        target_row = next(
            (r for r in all_rows if r.player_id == player_id and r.season == season),
            None,
        )
    if target_row is None:
        return []

    # Team-fit mode applies a per-feature penalty to the distance weights when
    # the subject duplicates a teammate's strength on that feature. Other modes
    # use the baseline SIMILARITY_STATS_V2 weights unchanged.
    weight_overrides: Optional[Dict[str, float]] = None
    if mode == "team_fit":
        weight_overrides = _team_fit_weight_overrides(target_row, all_rows, norms)

    target_raw = _raw_z(target_row, norms)
    if target_raw is None:
        return []
    target_vec = _weighted_vec(target_raw, weight_overrides)

    candidates = _build_candidate_pool(all_rows, target_row, mode, db)
    scored: List[Tuple[float, SeasonStat]] = []
    for row in candidates:
        cand_raw = _raw_z(row, norms)
        if cand_raw is None:
            continue
        cand_vec = _weighted_vec(cand_raw, weight_overrides)
        scored.append((_euclidean(target_vec, cand_vec), row))
    scored.sort(key=lambda pair: pair[0])
    top = scored[:n]

    # Player metadata for display
    player_ids = {row.player_id for _, row in top}
    players = {p.id: p for p in db.query(Player).filter(Player.id.in_(player_ids)).all()}

    # Batch-classify archetypes for each comp's (player_id, season).
    # Grouping by season lets the classifier cache reuse frames cheaply.
    from services.player_archetype_service import classify_player_archetype

    archetype_cache: Dict[Tuple[int, str], object] = {}

    def _archetype_for(pid: int, s: str):
        key = (pid, s)
        if key not in archetype_cache:
            archetype_cache[key] = classify_player_archetype(db, pid, s)
        return archetype_cache[key]

    results: List[dict] = []
    for dist, row in top:
        player = players.get(row.player_id)
        arch = _archetype_for(row.player_id, row.season)
        results.append({
            "player_id": row.player_id,
            "player_name": player.full_name if player else str(row.player_id),
            "headshot_url": player.headshot_url if player else None,
            "season": row.season,
            "team_abbreviation": row.team_abbreviation,
            "similarity_score": _distance_to_similarity(dist),
            "gp": row.gp,
            "pts_pg": row.pts_pg,
            "reb_pg": row.reb_pg,
            "ast_pg": row.ast_pg,
            "ts_pct": row.ts_pct,
            "usg_pct": row.usg_pct,
            "per": row.per,
            # Sprint 67 additions
            "archetype_key": getattr(arch, "archetype_key", None),
            "archetype_label": getattr(arch, "label", None),
            "archetype_confidence": getattr(arch, "confidence", None),
        })
    return results
