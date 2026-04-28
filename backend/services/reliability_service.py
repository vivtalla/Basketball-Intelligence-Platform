from __future__ import annotations

import math
import statistics
from typing import Iterable, List, Optional, Sequence, Tuple

from models.methodology import SampleContext, UncertaintyBand


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def reliability_score(sample_size: Optional[float], target_sample: float) -> float:
    """Monotonic 0-100 reliability score with diminishing returns.

    The score reaches 50 when sample_size == target_sample and approaches 100
    smoothly as sample grows. This gives every surface one intuitive reliability
    primitive without pretending all sample sizes have identical variance.
    """
    if sample_size is None or sample_size <= 0 or target_sample <= 0:
        return 0.0
    score = 100.0 * (float(sample_size) / (float(sample_size) + float(target_sample)))
    return round(clamp(score, 0.0, 100.0), 1)


def confidence_from_reliability(score: Optional[float]) -> str:
    value = float(score or 0.0)
    if value >= 70.0:
        return "high"
    if value >= 40.0:
        return "medium"
    return "low"


def empirical_bayes_rate(
    successes: float,
    attempts: float,
    prior_rate: float,
    prior_weight: float,
) -> float:
    if attempts < 0 or successes < 0:
        raise ValueError("successes and attempts must be non-negative")
    if prior_weight < 0:
        raise ValueError("prior_weight must be non-negative")
    denominator = float(attempts) + float(prior_weight)
    if denominator <= 0:
        return float(prior_rate)
    posterior = (float(successes) + float(prior_rate) * float(prior_weight)) / denominator
    return posterior


def empirical_bayes_mean(
    observed_mean: Optional[float],
    sample_size: float,
    prior_mean: float,
    prior_weight: float,
) -> float:
    if observed_mean is None or sample_size <= 0:
        return float(prior_mean)
    denominator = float(sample_size) + float(prior_weight)
    if denominator <= 0:
        return float(observed_mean)
    return (
        float(observed_mean) * float(sample_size)
        + float(prior_mean) * float(prior_weight)
    ) / denominator


def normal_uncertainty_band(
    mean: Optional[float],
    sample_size: Optional[int],
    std_dev: Optional[float],
    level: float = 0.90,
) -> UncertaintyBand:
    if mean is None or sample_size is None or sample_size <= 1 or std_dev is None:
        return UncertaintyBand(level=level, method="insufficient_sample")
    # z=1.64 is the two-sided normal approximation for a 90% interval.
    z_value = 1.64 if abs(level - 0.90) < 1e-9 else 1.96
    margin = z_value * (float(std_dev) / math.sqrt(float(sample_size)))
    return UncertaintyBand(
        lower=round(float(mean) - margin, 4),
        upper=round(float(mean) + margin, 4),
        level=level,
        method="normal_approximation",
    )


def wilson_interval(successes: float, attempts: float, level: float = 0.90) -> UncertaintyBand:
    if attempts <= 0:
        return UncertaintyBand(level=level, method="insufficient_sample")
    z_value = 1.64 if abs(level - 0.90) < 1e-9 else 1.96
    phat = float(successes) / float(attempts)
    denom = 1.0 + (z_value * z_value / float(attempts))
    center = (phat + (z_value * z_value) / (2.0 * float(attempts))) / denom
    margin = (
        z_value
        * math.sqrt((phat * (1.0 - phat) + (z_value * z_value) / (4.0 * float(attempts))) / float(attempts))
        / denom
    )
    return UncertaintyBand(
        lower=round(max(0.0, center - margin), 4),
        upper=round(min(1.0, center + margin), 4),
        level=level,
        method="wilson_score",
    )


def robust_zscores(values: Sequence[Optional[float]]) -> List[Optional[float]]:
    clean = [float(value) for value in values if value is not None]
    if len(clean) < 2:
        return [0.0 if value is not None else None for value in values]
    median = statistics.median(clean)
    deviations = [abs(value - median) for value in clean]
    mad = statistics.median(deviations)
    if mad <= 0:
        return [0.0 if value is not None else None for value in values]
    scale = 1.4826 * mad
    return [
        None if value is None else round((float(value) - median) / scale, 4)
        for value in values
    ]


def winsorized_zscores(values: Sequence[Optional[float]], lower_pct: float = 0.05, upper_pct: float = 0.95) -> List[Optional[float]]:
    clean = sorted(float(value) for value in values if value is not None)
    if len(clean) < 2:
        return [0.0 if value is not None else None for value in values]
    lower_index = int((len(clean) - 1) * lower_pct)
    upper_index = int((len(clean) - 1) * upper_pct)
    lower = clean[lower_index]
    upper = clean[upper_index]
    clipped = [min(max(float(value), lower), upper) for value in clean]
    mean = statistics.mean(clipped)
    std = statistics.stdev(clipped) or 1.0
    return [
        None if value is None else round((min(max(float(value), lower), upper) - mean) / std, 4)
        for value in values
    ]


def percentile_rank(value: Optional[float], values: Iterable[float]) -> Optional[float]:
    if value is None:
        return None
    pool = list(values)
    if not pool:
        return None
    below = sum(1 for item in pool if item < value)
    equal = sum(1 for item in pool if item == value)
    return round(((below + 0.5 * equal) / float(len(pool))) * 100.0, 2)


def sample_context(
    sample_size: Optional[int],
    minimum_recommended: Optional[int],
    population_size: Optional[int] = None,
    effective_sample_size: Optional[float] = None,
    notes: Optional[List[str]] = None,
) -> SampleContext:
    return SampleContext(
        sample_size=sample_size,
        effective_sample_size=effective_sample_size,
        population_size=population_size,
        minimum_recommended=minimum_recommended,
        notes=list(notes or []),
    )
