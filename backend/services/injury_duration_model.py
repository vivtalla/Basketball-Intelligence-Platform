"""Empirical injury-duration model.

Sprint 78 FO5. Given a body part + age + recurrence flag, returns a
DurationEstimate (median, p25, p75, sample size, fallback flag) sourced from
the `player_injury_history` table.

Falls back to a hardcoded prior keyed on body part when the cohort sample
is too small (< MIN_SAMPLE) to be informative. Hardcoded medians come
from publicly published averages and should be treated as sanity-check
priors, not analytical truth — confidence is reflected by the
`is_fallback` flag on the returned model.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from db.models import Player, PlayerInjuryHistory
from models.injury import DurationEstimate, SimilarPastInjury


MIN_SAMPLE = 5

# Hardcoded prior — median games missed per body part. Used when the
# empirical cohort under MIN_SAMPLE rows. P25/P75 derived as 0.6x and 1.6x
# the median to give a non-degenerate range.
HARDCODED_PRIOR: Dict[str, int] = {
    "knee": 14,
    "ankle": 7,
    "hamstring": 9,
    "lower-back": 5,
    "shoulder": 11,
    "finger": 3,
    "calf": 8,
    "foot": 12,
    "wrist": 6,
    "groin": 6,
}
DEFAULT_PRIOR = 8


def _normalize_body_part(value: Optional[str]) -> str:
    return (value or "").strip().lower().replace("_", "-")


def _age_band(age: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    """Return (lower, upper) age window for cohort filtering.

    None age → no age filter.
    """
    if age is None:
        return (None, None)
    return (max(18.0, age - 3.0), age + 3.0)


def _percentile(sorted_values: List[int], pct: float) -> int:
    """Linear-interpolation percentile on a pre-sorted list of ints."""
    if not sorted_values:
        return 0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = pct * (len(sorted_values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = rank - lo
    return int(round(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac))


def _hardcoded_estimate(body_part: str) -> DurationEstimate:
    median = HARDCODED_PRIOR.get(body_part, DEFAULT_PRIOR)
    return DurationEstimate(
        body_part=body_part,
        sample_size=0,
        median_games=median,
        p25_games=max(1, int(round(median * 0.6))),
        p75_games=int(round(median * 1.6)),
        mean_games=float(median),
        is_fallback=True,
        fallback_reason="hardcoded_prior",
        cohort_age_low=None,
        cohort_age_high=None,
        cohort_recurrence=None,
    )


def expected_duration(
    db: Session,
    body_part: str,
    age: Optional[float] = None,
    is_recurring: Optional[bool] = None,
) -> DurationEstimate:
    """Empirical duration distribution for a (body_part, age, recurrence) cohort.

    Cohort selection (in order of falloff):
      1. Strict: body_part + age band + recurrence flag.
      2. Loosen recurrence (same body_part + age band).
      3. Loosen age (same body_part).
      4. Hardcoded prior keyed on body_part.

    First cohort with >= MIN_SAMPLE rows wins.
    """
    body_part = _normalize_body_part(body_part)
    if not body_part:
        return _hardcoded_estimate("")

    age_low, age_high = _age_band(age)

    base_query = db.query(PlayerInjuryHistory.games_missed).filter(
        PlayerInjuryHistory.body_part == body_part,
        PlayerInjuryHistory.games_missed.isnot(None),
    )

    cohort_age_low: Optional[float] = None
    cohort_age_high: Optional[float] = None
    cohort_recurrence: Optional[bool] = None

    # Tier 1: full cohort (body_part + age + recurrence).
    games_list: List[int] = []
    if age_low is not None and is_recurring is not None:
        rows = base_query.filter(
            PlayerInjuryHistory.age_at_start >= age_low,
            PlayerInjuryHistory.age_at_start <= age_high,
            PlayerInjuryHistory.is_recurring == is_recurring,
        ).all()
        if len(rows) >= MIN_SAMPLE:
            games_list = sorted(int(row[0]) for row in rows if row[0] is not None)
            cohort_age_low = age_low
            cohort_age_high = age_high
            cohort_recurrence = is_recurring

    # Tier 2: drop recurrence flag.
    if not games_list and age_low is not None:
        rows = base_query.filter(
            PlayerInjuryHistory.age_at_start >= age_low,
            PlayerInjuryHistory.age_at_start <= age_high,
        ).all()
        if len(rows) >= MIN_SAMPLE:
            games_list = sorted(int(row[0]) for row in rows if row[0] is not None)
            cohort_age_low = age_low
            cohort_age_high = age_high
            cohort_recurrence = None

    # Tier 3: drop age band.
    if not games_list:
        rows = base_query.all()
        if len(rows) >= MIN_SAMPLE:
            games_list = sorted(int(row[0]) for row in rows if row[0] is not None)
            cohort_age_low = None
            cohort_age_high = None
            cohort_recurrence = None

    # Tier 4: fallback to hardcoded prior.
    if not games_list:
        return _hardcoded_estimate(body_part)

    median = _percentile(games_list, 0.50)
    p25 = _percentile(games_list, 0.25)
    p75 = _percentile(games_list, 0.75)
    mean = sum(games_list) / float(len(games_list))

    return DurationEstimate(
        body_part=body_part,
        sample_size=len(games_list),
        median_games=median,
        p25_games=p25,
        p75_games=p75,
        mean_games=round(mean, 2),
        is_fallback=False,
        fallback_reason=None,
        cohort_age_low=cohort_age_low,
        cohort_age_high=cohort_age_high,
        cohort_recurrence=cohort_recurrence,
    )


def find_similar_past_injuries(
    db: Session,
    body_part: str,
    age: Optional[float] = None,
    limit: int = 3,
    exclude_player_id: Optional[int] = None,
) -> List[SimilarPastInjury]:
    """Return up to `limit` past injuries closest to the (body_part, age) target.

    Used to anchor the duration estimate with concrete examples a user
    can recognize. Sort key: smallest age delta first, then most recent
    started_on. Excludes the current player so the panel doesn't only
    show that player's own history.
    """
    body_part = _normalize_body_part(body_part)
    if not body_part:
        return []

    query = (
        db.query(PlayerInjuryHistory, Player.full_name)
        .join(Player, Player.id == PlayerInjuryHistory.player_id)
        .filter(PlayerInjuryHistory.body_part == body_part)
        .filter(PlayerInjuryHistory.games_missed.isnot(None))
    )
    if exclude_player_id is not None:
        query = query.filter(PlayerInjuryHistory.player_id != exclude_player_id)

    rows = query.all()
    if not rows:
        return []

    def _sort_key(item):
        injury, _name = item
        age_delta = (
            abs(float(injury.age_at_start) - float(age))
            if age is not None and injury.age_at_start is not None
            else 99.0
        )
        # Negate started_on for stable recent-first secondary sort.
        recency = injury.started_on.toordinal() if injury.started_on else 0
        return (age_delta, -recency)

    rows.sort(key=_sort_key)

    similar: List[SimilarPastInjury] = []
    for injury, name in rows[:limit]:
        similar.append(
            SimilarPastInjury(
                player_id=injury.player_id,
                player_name=name,
                season=injury.season,
                body_part=injury.body_part,
                severity=injury.severity,
                started_on=injury.started_on,
                resolved_on=injury.resolved_on,
                games_missed=injury.games_missed,
                age_at_start=injury.age_at_start,
                is_recurring=bool(injury.is_recurring),
            )
        )
    return similar


def player_age(player: Optional[Player], today_year: Optional[int] = None) -> Optional[float]:
    """Best-effort age estimate from `Player.birth_date` (string field)."""
    if player is None or not player.birth_date:
        return None
    raw = str(player.birth_date).strip()
    # Common formats stored historically: "1984-12-30", "1984-12-30T00:00:00", "DEC 30, 1984"
    year: Optional[int] = None
    if len(raw) >= 4 and raw[:4].isdigit():
        year = int(raw[:4])
    else:
        for token in raw.replace(",", " ").split():
            if token.isdigit() and len(token) == 4:
                year = int(token)
                break
    if year is None:
        return None
    if today_year is None:
        from datetime import date

        today_year = date.today().year
    return float(today_year - year)


def player_recurrence_for_body_part(
    db: Session, player_id: int, body_part: str
) -> bool:
    """True if the player has any prior recorded injury to the same body part."""
    body_part = _normalize_body_part(body_part)
    if not body_part:
        return False
    exists = (
        db.query(PlayerInjuryHistory.id)
        .filter(
            PlayerInjuryHistory.player_id == player_id,
            PlayerInjuryHistory.body_part == body_part,
        )
        .first()
    )
    return exists is not None


# Re-exported so test/import call sites can reach the prior table without
# poking at private state.
__all__ = [
    "MIN_SAMPLE",
    "HARDCODED_PRIOR",
    "DEFAULT_PRIOR",
    "expected_duration",
    "find_similar_past_injuries",
    "player_age",
    "player_recurrence_for_body_part",
]


# Suppress unused-import warning — `and_`/`or_` are kept for downstream
# extension (e.g. when we add severity weighting).
_ = (and_, or_)
