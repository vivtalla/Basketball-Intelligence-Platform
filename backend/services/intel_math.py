from __future__ import annotations

import math
import statistics
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, TypeVar

T = TypeVar("T")


def safe_round(value: Optional[float], digits: int = 2) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), digits)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def rate(numerator: Optional[float], denominator: Optional[float], digits: int = 4) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(float(numerator) / float(denominator), digits)


def estimate_possessions(
    fga: Optional[float],
    oreb: Optional[float],
    tov: Optional[float],
    fta: Optional[float],
) -> Optional[float]:
    if fga is None or oreb is None or tov is None or fta is None:
        return None
    possessions = float(fga) - float(oreb) + float(tov) + (0.44 * float(fta))
    if possessions <= 0:
        return None
    return possessions


def ts_pct(pts: Optional[float], fga: Optional[float], fta: Optional[float]) -> Optional[float]:
    if pts is None or fga is None or fta is None:
        return None
    denominator = 2.0 * (float(fga) + (0.44 * float(fta)))
    if denominator <= 0:
        return None
    return float(pts) / denominator


def efg_pct(fgm: Optional[float], fg3m: Optional[float], fga: Optional[float]) -> Optional[float]:
    if fgm is None or fg3m is None or fga is None or fga == 0:
        return None
    return (float(fgm) + (0.5 * float(fg3m))) / float(fga)


def turnover_rate(
    tov: Optional[float],
    fga: Optional[float],
    fta: Optional[float],
    extra_plays: Optional[float] = None,
) -> Optional[float]:
    if tov is None:
        return None
    denominator = float(fga or 0.0) + (0.44 * float(fta or 0.0)) + float(extra_plays or 0.0)
    if denominator <= 0:
        return None
    return float(tov) / denominator


def oreb_rate(
    oreb: Optional[float],
    dreb_allowed: Optional[float],
) -> Optional[float]:
    if oreb is None or dreb_allowed is None:
        return None
    denominator = float(oreb) + float(dreb_allowed)
    if denominator <= 0:
        return None
    return float(oreb) / denominator


def ftr(fta: Optional[float], fga: Optional[float]) -> Optional[float]:
    if fta is None or fga is None or fga == 0:
        return None
    return float(fta) / float(fga)


def three_point_rate(fg3a: Optional[float], fga: Optional[float]) -> Optional[float]:
    if fg3a is None or fga is None or fga == 0:
        return None
    return float(fg3a) / float(fga)


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> Optional[float]:
    if not values or not weights or len(values) != len(weights):
        return None
    total_weight = float(sum(weights))
    if total_weight == 0:
        return None
    return sum(value * weight for value, weight in zip(values, weights)) / total_weight


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return sum(clean) / float(len(clean))


def median(values: Iterable[Optional[float]]) -> Optional[float]:
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return None
    return statistics.median(clean)


def percentile_rank(value: Optional[float], values: Sequence[float]) -> Optional[float]:
    if value is None or not values:
        return None
    below = sum(1 for item in values if item < value)
    equal = sum(1 for item in values if item == value)
    return ((below + 0.5 * equal) / float(len(values))) * 100.0


def zscore_map(values_by_key: Dict[T, float]) -> Dict[T, float]:
    values = list(values_by_key.values())
    if len(values) < 2:
        return {key: 0.0 for key in values_by_key}
    mean_value = statistics.mean(values)
    std_value = statistics.stdev(values)
    if not std_value:
        return {key: 0.0 for key in values_by_key}
    return {
        key: (value - mean_value) / std_value
        for key, value in values_by_key.items()
    }


def top_k_by_abs(values: Sequence[Tuple[str, float]], k: int = 3) -> List[Tuple[str, float]]:
    return sorted(values, key=lambda item: abs(item[1]), reverse=True)[:k]


def normalize_unit(value: Optional[float], scale: float = 100.0) -> Optional[float]:
    if value is None:
        return None
    return float(value) / scale


def share_of_total(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return float(numerator) / float(denominator)

