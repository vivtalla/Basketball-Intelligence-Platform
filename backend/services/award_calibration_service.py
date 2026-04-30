"""Sprint 79 Stream A1 — coordinate-descent calibration of MVP Award Case modifier weights.

Methodology spec: ``specs/methodology-future-modeling.md#1``.

The Award Case composite today reuses the Basketball Value pillars and adds
five capped narrative modifiers with hand-tuned weights:

    team_framing       0.08
    eligibility_pressure 0.08
    clutch             0.06
    momentum           0.05
    signature_games    0.05

This module fits those weights against historical MVP voting outcomes via:

    Award Case_i = B_i + W . M_i
    minimize sum_i (rank_predicted - rank_observed)^2

Subject to: W >= 0, sum(W) <= 0.40 (so Basketball Value still dominates).

The fit uses coordinate-descent over a 5-dimensional bounded space + leave-one-
season-out cross-validation. Pure-Python so we don't add sklearn.

CALIBRATION DATA STATUS (Sprint 79):
The award_voting table is populated (12+ seasons), but historical Basketball
Value scores and modifier vectors per candidate are NOT yet materialized — they
require retroactive runs of mvp_service against past seasons, which is its
own materialization sprint. Until that lands, ``calibrate_award_case_weights``
returns the existing hand-tuned weights with a ``calibration_pending=True`` flag.

The math, validation, and registry wiring all ship in Sprint 79 so the moment
historical modifier data lands, the calibration runs as a one-liner.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import AwardCaseCandidate, AwardVote

log = logging.getLogger(__name__)


# Default weights — published Sprint 76 hand-tuned priors, used until calibration
# data is materialized.
DEFAULT_AWARD_CASE_WEIGHTS = {
    "team_framing": 0.08,
    "eligibility_pressure": 0.08,
    "clutch": 0.06,
    "momentum": 0.05,
    "signature_games": 0.05,
}

MODIFIER_KEYS = ("team_framing", "eligibility_pressure", "clutch", "momentum", "signature_games")
WEIGHT_SUM_CAP = 0.40
MAX_PILLAR_DRIFT = 0.04   # spec: calibrated weights move <= 0.04 absolute on any pillar
MIN_FOLDS_REQUIRED = 5    # don't trust LOO-CV averages with fewer than 5 folds
SPEARMAN_TARGET = 0.7     # acceptance criterion


# ---------------------------------------------------------------------------
# Pure-math primitives — testable in isolation against synthetic data.
# ---------------------------------------------------------------------------

def _spearman_correlation(predicted: List[float], observed: List[float]) -> float:
    """Spearman rank correlation between two equal-length value lists.

    Returns 0.0 when input is degenerate (length < 2 or no rank variance).
    """
    n = len(predicted)
    if n < 2 or len(observed) != n:
        return 0.0

    def _rank(values: List[float]) -> List[float]:
        order = sorted(range(n), key=lambda i: values[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and values[order[j + 1]] == values[order[i]]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[order[k]] = avg_rank
            i = j + 1
        return ranks

    rp = _rank(predicted)
    ro = _rank(observed)
    mean_p = sum(rp) / n
    mean_o = sum(ro) / n
    num = sum((rp[i] - mean_p) * (ro[i] - mean_o) for i in range(n))
    den_p = sum((rp[i] - mean_p) ** 2 for i in range(n)) ** 0.5
    den_o = sum((ro[i] - mean_o) ** 2 for i in range(n)) ** 0.5
    if den_p == 0 or den_o == 0:
        return 0.0
    return num / (den_p * den_o)


def _award_case_score(basketball_value: float, modifier_vector: List[float], weights: List[float]) -> float:
    """Award Case = Basketball Value + W . M."""
    return basketball_value + sum(weights[k] * modifier_vector[k] for k in range(len(weights)))


def _evaluate_weights(
    candidates: List[Dict[str, object]],
    weights: List[float],
) -> float:
    """Compute mean negative MSE between predicted Award Case rank and observed rank.

    Higher (less negative) is better. Used as the objective for coordinate descent.
    """
    if not candidates:
        return 0.0

    scored = [
        _award_case_score(c["basketball_value"], c["modifier_vector"], weights) for c in candidates
    ]
    observed = [c["observed_share"] for c in candidates]
    # Negative MSE on rank order means "minimize rank distance" -> "maximize objective".
    rho = _spearman_correlation(scored, observed)
    return rho


def _project_to_constraints(weights: List[float]) -> List[float]:
    """Enforce W >= 0 and sum(W) <= WEIGHT_SUM_CAP.

    Negative components clipped to 0; if sum exceeds cap, scale uniformly.
    """
    clipped = [max(0.0, w) for w in weights]
    total = sum(clipped)
    if total > WEIGHT_SUM_CAP:
        scale = WEIGHT_SUM_CAP / total
        clipped = [w * scale for w in clipped]
    return clipped


def coordinate_descent_fit(
    candidates: List[Dict[str, object]],
    *,
    initial_weights: Optional[List[float]] = None,
    grid_resolution: float = 0.01,
    max_iterations: int = 50,
    grid_radius: float = 0.06,
) -> Tuple[List[float], float]:
    """Fit weights via coordinate descent in a 5D bounded space.

    Returns (best_weights, best_objective). Objective is Spearman correlation
    between predicted Award Case score and observed point share.
    """
    if not candidates:
        return list(DEFAULT_AWARD_CASE_WEIGHTS.values()), 0.0

    weights = list(initial_weights) if initial_weights else [DEFAULT_AWARD_CASE_WEIGHTS[k] for k in MODIFIER_KEYS]
    weights = _project_to_constraints(weights)
    best_score = _evaluate_weights(candidates, weights)

    for _ in range(max_iterations):
        improved = False
        for axis in range(len(weights)):
            anchor = weights[axis]
            best_anchor = anchor
            steps = int(grid_radius / grid_resolution)
            for delta in range(-steps, steps + 1):
                candidate = anchor + delta * grid_resolution
                if candidate < 0:
                    continue
                trial = list(weights)
                trial[axis] = candidate
                trial = _project_to_constraints(trial)
                score = _evaluate_weights(candidates, trial)
                if score > best_score + 1e-6:
                    best_score = score
                    best_anchor = candidate
                    improved = True
            weights[axis] = best_anchor
            weights = _project_to_constraints(weights)
        if not improved:
            break

    return weights, best_score


def leave_one_season_out_cv(
    candidates_by_season: Dict[str, List[Dict[str, object]]],
) -> Tuple[List[float], float, int]:
    """Leave-one-season-out cross-validation.

    Returns: (mean_weights_across_folds, mean_held_out_spearman, fold_count).
    """
    seasons = sorted(candidates_by_season.keys())
    if len(seasons) < MIN_FOLDS_REQUIRED:
        return list(DEFAULT_AWARD_CASE_WEIGHTS.values()), 0.0, len(seasons)

    fold_weights: List[List[float]] = []
    fold_spearmans: List[float] = []
    for held_out in seasons:
        train = [c for s, rows in candidates_by_season.items() if s != held_out for c in rows]
        weights, _ = coordinate_descent_fit(train)
        held_set = candidates_by_season[held_out]
        if held_set:
            predicted = [
                _award_case_score(c["basketball_value"], c["modifier_vector"], weights)
                for c in held_set
            ]
            observed = [c["observed_share"] for c in held_set]
            rho = _spearman_correlation(predicted, observed)
            fold_spearmans.append(rho)
            fold_weights.append(weights)

    if not fold_weights:
        return list(DEFAULT_AWARD_CASE_WEIGHTS.values()), 0.0, 0

    n_axes = len(fold_weights[0])
    mean_weights = [
        sum(fw[i] for fw in fold_weights) / len(fold_weights) for i in range(n_axes)
    ]
    mean_spearman = sum(fold_spearmans) / len(fold_spearmans)
    return mean_weights, mean_spearman, len(fold_weights)


def _enforce_drift_cap(
    calibrated_weights: List[float],
    prior_weights: List[float],
    cap: float = MAX_PILLAR_DRIFT,
) -> List[float]:
    """Clamp calibrated weights so each pillar moves at most ``cap`` absolute from the prior.

    Per spec: 'calibration tunes, doesn't replace, the expert priors.'
    """
    return [
        max(prior - cap, min(prior + cap, calibrated))
        for calibrated, prior in zip(calibrated_weights, prior_weights)
    ]


# ---------------------------------------------------------------------------
# Public API — invoked at module import in mvp_service when the data lands.
# ---------------------------------------------------------------------------

def _load_calibration_dataset(
    db: Session, award_type: str = "MVP"
) -> Dict[str, List[Dict[str, object]]]:
    """Join award_voting × award_case_candidates → per-season candidate lists.

    Returns ``{season: [{basketball_value, modifier_vector, observed_share}, ...]}``.
    Only candidates with both an observed vote share AND a materialized
    modifier vector are included.
    """
    vote_index: Dict[Tuple[int, str], float] = {}
    for vote in db.query(AwardVote).filter(AwardVote.award_type == award_type).all():
        vote_index[(vote.player_id, vote.season)] = float(vote.total_award_points or 0.0)

    out: Dict[str, List[Dict[str, object]]] = {}
    for cand in (
        db.query(AwardCaseCandidate)
        .filter(AwardCaseCandidate.award_type == award_type)
        .all()
    ):
        share = vote_index.get((cand.player_id, cand.season))
        if share is None:
            continue
        out.setdefault(cand.season, []).append({
            "basketball_value": float(cand.basketball_value),
            "modifier_vector": [
                float(cand.modifier_team_framing),
                float(cand.modifier_eligibility_pressure),
                float(cand.modifier_clutch),
                float(cand.modifier_momentum),
                float(cand.modifier_signature_games),
            ],
            "observed_share": share,
        })
    return out


def calibrate_award_case_weights(db: Session) -> Dict[str, object]:
    """Run leave-one-season-out coordinate-descent fit; return a result envelope.

    Sprint 81: uses the materialized ``award_case_candidates`` table when
    populated. If the candidate set is too thin (< MIN_FOLDS_REQUIRED seasons)
    or LOO-CV Spearman misses ``SPEARMAN_TARGET``, returns the hand-tuned
    defaults with ``calibration_pending=True`` and surfaces the failure in
    notes. The drift cap keeps calibrated weights within ±0.04 of the priors.

    Returns a dict containing:
        weights: dict[str, float] keyed by modifier name
        cross_validated_spearman: float
        fold_count: int
        last_calibrated_season: str | None
        calibration_pending: bool      — True when historical modifier data isn't materialized
        notes: list[str]
    """
    vote_count = db.query(AwardVote).count()
    if vote_count == 0:
        return {
            "weights": dict(DEFAULT_AWARD_CASE_WEIGHTS),
            "cross_validated_spearman": 0.0,
            "fold_count": 0,
            "last_calibrated_season": None,
            "calibration_pending": True,
            "notes": ["award_voting table is empty; using hand-tuned default weights"],
        }

    last_season = (
        db.query(AwardVote.season)
        .order_by(AwardVote.season.desc())
        .limit(1)
        .scalar()
    )

    candidate_count = db.query(AwardCaseCandidate).count()
    if candidate_count == 0:
        return {
            "weights": dict(DEFAULT_AWARD_CASE_WEIGHTS),
            "cross_validated_spearman": 0.0,
            "fold_count": 0,
            "last_calibrated_season": last_season,
            "calibration_pending": True,
            "notes": [
                "award_voting populated ({0} rows) but award_case_candidates is empty.".format(vote_count),
                "Run `python data/materialize_award_modifiers.py` to populate Basketball Value + modifier vectors.",
            ],
        }

    candidates_by_season = _load_calibration_dataset(db)
    season_count = len(candidates_by_season)
    if season_count < MIN_FOLDS_REQUIRED:
        return {
            "weights": dict(DEFAULT_AWARD_CASE_WEIGHTS),
            "cross_validated_spearman": 0.0,
            "fold_count": season_count,
            "last_calibrated_season": last_season,
            "calibration_pending": True,
            "notes": [
                "Only {0} season(s) of materialized candidates; LOO-CV requires >= {1}.".format(
                    season_count, MIN_FOLDS_REQUIRED
                ),
                "Add more seasons to award_voting + re-run materialize_award_modifiers.py.",
            ],
        }

    mean_weights, mean_spearman, fold_count = leave_one_season_out_cv(candidates_by_season)
    if mean_spearman < SPEARMAN_TARGET:
        return {
            "weights": dict(DEFAULT_AWARD_CASE_WEIGHTS),
            "cross_validated_spearman": float(mean_spearman),
            "fold_count": fold_count,
            "last_calibrated_season": last_season,
            "calibration_pending": True,
            "notes": [
                "LOO-CV Spearman {0:.3f} < target {1:.2f}; calibrated weights would not improve on priors.".format(
                    mean_spearman, SPEARMAN_TARGET
                ),
                "Returning hand-tuned defaults until calibration cohort is richer or proxies improve.",
            ],
        }

    prior_weights = [DEFAULT_AWARD_CASE_WEIGHTS[k] for k in MODIFIER_KEYS]
    capped = _enforce_drift_cap(mean_weights, prior_weights)

    return {
        "weights": {k: float(capped[i]) for i, k in enumerate(MODIFIER_KEYS)},
        "cross_validated_spearman": float(mean_spearman),
        "fold_count": fold_count,
        "last_calibrated_season": last_season,
        "calibration_pending": False,
        "notes": [
            "Calibrated against {0} candidate-seasons; LOO-CV Spearman = {1:.3f}.".format(
                sum(len(v) for v in candidates_by_season.values()), mean_spearman
            ),
            "Drift cap (+/-0.04 per pillar) applied; weights tune the hand-tuned priors rather than replace them.",
        ],
    }


# Module-level constant consumed by mvp_service.py at import.
# Until calibration_pending is False, this matches DEFAULT_AWARD_CASE_WEIGHTS.
# At runtime, mvp_service can call calibrate_award_case_weights(db) to fetch
# live-fit weights from the materialized table.
CALIBRATED_AWARD_CASE_WEIGHTS = dict(DEFAULT_AWARD_CASE_WEIGHTS)
