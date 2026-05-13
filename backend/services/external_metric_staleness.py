"""Sprint 98 Stream B3 — External-metric staleness surfacing.

``SeasonStat.external_metrics_meta`` stores ``{source, as_of, note}`` per
metric (LEBRON / RAPTOR / EPM / PIPM / RAPM) as opaque JSON. Without a
helper, the as_of date is invisible to API consumers, so analytics can
quietly use weeks-stale metrics. This module exposes the staleness
information so response models can surface it.

Each external metric ages independently — LEBRON might be 3 days old
while RAPTOR is 4 weeks old. The helper returns per-metric ages so the
caller can decide which to display or hide.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Mapping, Optional

KNOWN_METRICS = ("lebron", "raptor", "epm", "pipm", "rapm", "darko", "bpm", "vorp")

STALE_THRESHOLD_DAYS = 21  # >3 weeks is amber; ≤ is silent


def metric_age_days(
    meta_json: Optional[Mapping],
    metric: str,
    now: Optional[date] = None,
) -> Optional[int]:
    """Return the age in days for one metric, or None if unknown.

    Args:
        meta_json: parsed ``external_metrics_meta`` JSON from SeasonStat.
            Expected shape: ``{"epm": {"source": "...", "as_of": "YYYY-MM-DD"}}``.
        metric: lowercase metric name, e.g. ``"epm"``.
        now: injected for testing; defaults to ``date.today()``.

    Returns:
        Days since ``as_of`` (>=0) or ``None`` if the metric isn't in
        meta, has no ``as_of``, or the value is malformed.
    """
    if not meta_json or not isinstance(meta_json, Mapping):
        return None
    entry = meta_json.get(metric.lower())
    if not entry or not isinstance(entry, Mapping):
        return None
    as_of_raw = entry.get("as_of")
    if not as_of_raw:
        return None
    try:
        as_of = datetime.strptime(str(as_of_raw)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    today = now or date.today()
    delta = (today - as_of).days
    return max(delta, 0)


def metric_as_of(
    meta_json: Optional[Mapping],
    metric: str,
) -> Optional[str]:
    """Return the raw ``as_of`` string for one metric, or None if unknown.

    Useful when the caller wants to render the date directly without
    computing an age (e.g. ``"as of 2026-04-12"``).
    """
    if not meta_json or not isinstance(meta_json, Mapping):
        return None
    entry = meta_json.get(metric.lower())
    if not entry or not isinstance(entry, Mapping):
        return None
    as_of_raw = entry.get("as_of")
    if not as_of_raw:
        return None
    return str(as_of_raw)[:10]


def staleness_snapshot(
    meta_json: Optional[Mapping],
    now: Optional[date] = None,
) -> Dict[str, Dict]:
    """Return a per-metric staleness map for surfacing in response models.

    Output shape:
        ``{"epm": {"as_of": "2026-04-12", "age_days": 28, "stale": True}, ...}``

    Only includes metrics actually present in ``meta_json``. Use this in
    Pydantic response models as ``metric_staleness: Optional[Dict[str, ...]]``.
    """
    if not meta_json or not isinstance(meta_json, Mapping):
        return {}
    out: Dict[str, Dict] = {}
    for metric in meta_json.keys():
        as_of = metric_as_of(meta_json, metric)
        if not as_of:
            continue
        age = metric_age_days(meta_json, metric, now=now)
        out[metric.lower()] = {
            "as_of": as_of,
            "age_days": age,
            "stale": (age is not None and age > STALE_THRESHOLD_DAYS),
        }
    return out


__all__ = [
    "KNOWN_METRICS",
    "STALE_THRESHOLD_DAYS",
    "metric_age_days",
    "metric_as_of",
    "staleness_snapshot",
]
