from __future__ import annotations

import math
import statistics
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from models.methodology import SampleContext, UncertaintyBand


# Two-sided normal critical values for the most common documented confidence
# levels. Anything outside this table falls back to the closest listed level so
# the resulting interval is never quietly mis-calibrated against the requested
# `level`.
_Z_FOR_LEVEL = (
    (0.80, 1.282),
    (0.90, 1.645),
    (0.95, 1.960),
    (0.99, 2.576),
)


def _z_for_level(level: float) -> Tuple[float, float]:
    """Return (resolved_level, z_value) for a requested confidence level.

    Levels outside the supported table snap to the nearest supported level so
    callers always receive a properly-calibrated interval rather than a
    silently-wrong 1.96-fallback.
    """
    nearest = min(_Z_FOR_LEVEL, key=lambda entry: abs(entry[0] - float(level)))
    return nearest[0], nearest[1]


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
    if not 0.0 <= float(prior_rate) <= 1.0:
        raise ValueError("prior_rate must be in [0, 1]")
    if successes > attempts:
        raise ValueError("successes cannot exceed attempts")
    denominator = float(attempts) + float(prior_weight)
    if denominator <= 0:
        return float(prior_rate)
    posterior = (float(successes) + float(prior_rate) * float(prior_weight)) / denominator
    # Clamp guards against floating-point drift; the math itself is in [0,1] when
    # the inputs satisfy the validation above.
    return clamp(posterior, 0.0, 1.0)


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


def empirical_bayes_delta(
    observed_value: Optional[float],
    expected_value: Optional[float],
    sample_size: float,
    prior_weight: float,
) -> float:
    """Shrink observed-minus-expected deltas toward zero for thin samples."""
    if observed_value is None or expected_value is None:
        return 0.0
    denominator = float(sample_size) + float(prior_weight)
    if denominator <= 0:
        return 0.0
    raw_delta = float(observed_value) - float(expected_value)
    return raw_delta * (float(sample_size) / denominator)


def normal_uncertainty_band(
    mean: Optional[float],
    sample_size: Optional[int],
    std_dev: Optional[float],
    level: float = 0.90,
) -> UncertaintyBand:
    resolved_level, z_value = _z_for_level(level)
    if mean is None or sample_size is None or sample_size <= 1 or std_dev is None:
        return UncertaintyBand(level=resolved_level, method="insufficient_sample")
    margin = z_value * (float(std_dev) / math.sqrt(float(sample_size)))
    return UncertaintyBand(
        lower=round(float(mean) - margin, 4),
        upper=round(float(mean) + margin, 4),
        level=resolved_level,
        method="normal_approximation",
    )


def wilson_interval(successes: float, attempts: float, level: float = 0.90) -> UncertaintyBand:
    resolved_level, z_value = _z_for_level(level)
    if attempts <= 0:
        return UncertaintyBand(level=resolved_level, method="insufficient_sample")
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
        level=resolved_level,
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


def pearson_correlation(
    series_a: Sequence[Optional[float]],
    series_b: Sequence[Optional[float]],
) -> Optional[float]:
    """Pairwise Pearson correlation. Returns None when fewer than two complete
    pairs exist or either series has zero variance after pairing."""
    if len(series_a) != len(series_b):
        raise ValueError("series_a and series_b must have equal length")
    pairs = [
        (float(a), float(b))
        for a, b in zip(series_a, series_b)
        if a is not None and b is not None
    ]
    if len(pairs) < 2:
        return None
    mean_a = statistics.mean(a for a, _ in pairs)
    mean_b = statistics.mean(b for _, b in pairs)
    covariance = sum((a - mean_a) * (b - mean_b) for a, b in pairs)
    var_a = sum((a - mean_a) ** 2 for a, _ in pairs)
    var_b = sum((b - mean_b) ** 2 for _, b in pairs)
    if var_a <= 0 or var_b <= 0:
        return None
    return round(covariance / math.sqrt(var_a * var_b), 4)


def collinearity_warnings(
    series_by_label: Dict[str, Sequence[Optional[float]]],
    threshold: float = 0.85,
) -> List[str]:
    """Surface a plain-language warning for each pair of components whose
    pairwise Pearson correlation magnitude meets the threshold.

    The output is intentionally human-readable so callers can append it to
    existing `validation_warnings` lists without translating numeric matrices.
    """
    labels = list(series_by_label.keys())
    warnings_out: List[str] = []
    for index, label_a in enumerate(labels):
        for label_b in labels[index + 1 :]:
            corr = pearson_correlation(series_by_label[label_a], series_by_label[label_b])
            if corr is None:
                continue
            if abs(corr) >= float(threshold):
                warnings_out.append(
                    "{0} and {1} are highly correlated (r={2:+.2f}); the composite may double-count one signal.".format(
                        label_a,
                        label_b,
                        corr,
                    )
                )
    return warnings_out
