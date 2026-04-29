"""Win-probability trajectory + lead-tracker service.

Reads PostgreSQL ``play_by_play`` rows for a single game and emits two pure
derived series consumed by the Game Detail surface:

* :func:`compute_win_probability` — closed-form logistic WP at every scoring
  event plus quarter boundaries, with swing labels for >= 12pp single-event
  WP changes.
* :func:`compute_lead_tracker` — home lead at each minute boundary, padded to
  cover overtime if the game went past regulation.

The functions are intentionally pure and side-effect free: they only read PBP
rows and return Pydantic model lists. They are safe to call with no PBP data
present (in which case both return an empty list).
"""

from __future__ import annotations

import math
import re
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import PlayByPlay
from models.game import LeadPoint, WinProbPoint


# ---------------------------------------------------------------------------
# Tunable constants — coefficients are fit on a season's worth of NBA PBP and
# treated as hardcoded. Swing labels and the WP clamp avoid both unbounded
# log-odds and noise from sub-12pp shifts.
# ---------------------------------------------------------------------------

PERIOD_LENGTH_SECONDS = 720       # 12 minutes per regulation period
OT_LENGTH_SECONDS = 300           # 5 minutes per overtime period
REGULATION_SECONDS = PERIOD_LENGTH_SECONDS * 4  # 2880

BETA_INTERCEPT = 0.0
BETA_SCORE_DIFF = 0.16
# Positive sign so large leads "inflate as time burns" (per the spec comment):
# the magnitude of the score-diff contribution grows with seconds elapsed.
BETA_TIME_DECAY_PER_PT = 0.0003
BETA_POSSESSION_ARROW = 0.05

WP_CLAMP_LOW = 0.001
WP_CLAMP_HIGH = 0.999
SWING_THRESHOLD_PP = 0.12  # 12 percentage-point single-event swing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLOCK_RE = re.compile(r"PT(\d+)M([\d.]+)S")
_FALLBACK_RE = re.compile(r"(\d+):(\d+(?:\.\d+)?)")


def _parse_clock_seconds(clock: Optional[str]) -> float:
    """Parse the NBA ``PT05M30.00S`` clock format into seconds remaining in the period.

    Falls back to ``MM:SS`` form for legacy rows. Returns 0.0 on missing or
    unparseable input.
    """
    if not clock:
        return 0.0
    m = _CLOCK_RE.match(clock)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    m2 = _FALLBACK_RE.match(clock)
    if m2:
        return int(m2.group(1)) * 60 + float(m2.group(2))
    return 0.0


def _seconds_remaining(period: Optional[int], clock: Optional[str]) -> int:
    """Return seconds remaining in regulation given ``period`` and ``clock``.

    Periods 1-4 are regulation. Periods >=5 are overtime; the function returns
    0 for those (regulation is over). Missing period defaults to 1.
    """
    p = int(period) if period else 1
    period_clock = _parse_clock_seconds(clock)
    if p >= 5:
        return 0
    completed_periods = max(p - 1, 0)
    seconds_already_played_in_prior_periods = completed_periods * PERIOD_LENGTH_SECONDS
    seconds_remaining_in_current = max(0.0, period_clock)
    seconds_elapsed = seconds_already_played_in_prior_periods + (
        PERIOD_LENGTH_SECONDS - seconds_remaining_in_current
    )
    seconds_remaining = REGULATION_SECONDS - seconds_elapsed
    if seconds_remaining < 0:
        return 0
    return int(round(seconds_remaining))


def _seconds_elapsed(period: Optional[int], clock: Optional[str]) -> int:
    """Return seconds elapsed since tip, including overtime."""
    p = int(period) if period else 1
    period_clock = _parse_clock_seconds(clock)
    if p <= 4:
        completed_periods = max(p - 1, 0)
        prior = completed_periods * PERIOD_LENGTH_SECONDS
        elapsed_in_period = max(0.0, PERIOD_LENGTH_SECONDS - period_clock)
    else:
        prior = REGULATION_SECONDS + (p - 5) * OT_LENGTH_SECONDS
        elapsed_in_period = max(0.0, OT_LENGTH_SECONDS - period_clock)
    return int(round(prior + elapsed_in_period))


def _sigmoid(z: float) -> float:
    # Guard against overflow on extreme inputs.
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def _logistic_wp_home(
    score_diff: int,
    seconds_remaining: int,
    home_has_possession: Optional[bool],
) -> float:
    """Closed-form logistic WP for the home team.

    ``logit(WP_home) = beta_score_diff * score_diff
                       + beta_score_diff * beta_time_decay_per_pt
                          * score_diff * (REGULATION - seconds_remaining)
                       + beta_possession_arrow * possession_sign``

    Possession is optional; missing possession contributes 0.
    """
    elapsed = REGULATION_SECONDS - seconds_remaining
    if home_has_possession is True:
        possession_sign = 1
    elif home_has_possession is False:
        possession_sign = -1
    else:
        possession_sign = 0
    logit = (
        BETA_INTERCEPT
        + BETA_SCORE_DIFF * score_diff
        + BETA_SCORE_DIFF * BETA_TIME_DECAY_PER_PT * score_diff * elapsed
        + BETA_POSSESSION_ARROW * possession_sign
    )
    wp = _sigmoid(logit)
    if wp < WP_CLAMP_LOW:
        return WP_CLAMP_LOW
    if wp > WP_CLAMP_HIGH:
        return WP_CLAMP_HIGH
    return wp


def _is_scoring_event(action_type: Optional[str], sub_type: Optional[str]) -> bool:
    if not action_type or not sub_type:
        return False
    if sub_type != "made":
        return False
    return action_type in ("2pt", "3pt", "freethrow")


def _swing_label(
    prev_wp: float,
    new_wp: float,
    prev_score_diff: int,
    new_score_diff: int,
    action_type: Optional[str],
) -> Optional[str]:
    """Return a swing label if the WP shift exceeds ``SWING_THRESHOLD_PP``.

    The label tries to be informative: a 3pt make in clutch becomes
    "CLUTCH 3", a multi-point home swing becomes "+N RUN", an away swing
    becomes "-N RUN". Smaller-magnitude swings without a scoring event are
    labeled "TIMEOUT" as a generic momentum-shift placeholder.
    """
    delta = new_wp - prev_wp
    if abs(delta) < SWING_THRESHOLD_PP:
        return None
    score_swing = new_score_diff - prev_score_diff
    if action_type == "3pt" and abs(score_swing) >= 3:
        return "CLUTCH 3"
    if score_swing > 0:
        return "+{:d} RUN".format(int(score_swing))
    if score_swing < 0:
        return "{:d} RUN".format(int(score_swing))
    return "TIMEOUT"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_win_probability(db: Session, game_id: str) -> List[WinProbPoint]:
    """Emit a WP point at every scoring event + quarter boundaries.

    Returns one ``WinProbPoint`` per scoring event AND at each quarter
    boundary (start of Q1/Q2/Q3/Q4, plus overtime starts if applicable). WPs
    are bounded to ``[WP_CLAMP_LOW, WP_CLAMP_HIGH]``. Single-event swings of
    >=12pp are tagged via the ``event`` field.
    """
    rows = (
        db.query(PlayByPlay)
        .filter(PlayByPlay.game_id == game_id)
        .order_by(PlayByPlay.action_number.asc())
        .all()
    )
    if not rows:
        return []

    points: List[WinProbPoint] = []
    score_home = 0
    score_away = 0
    prev_wp: Optional[float] = None
    seen_period_starts = set()

    for row in rows:
        if row.score_home is not None:
            score_home = int(row.score_home)
        if row.score_away is not None:
            score_away = int(row.score_away)

        period = row.period or 1
        seconds_remaining = _seconds_remaining(period, row.clock)
        seconds_elapsed = _seconds_elapsed(period, row.clock)
        score_diff = score_home - score_away

        # Inject a quarter-boundary point the first time we see each period.
        # This ensures Q1/Q2/Q3/Q4 (and OT) starts always anchor the curve.
        if period not in seen_period_starts:
            seen_period_starts.add(period)
            if period <= 4:
                boundary_seconds_remaining = REGULATION_SECONDS - (period - 1) * PERIOD_LENGTH_SECONDS
                boundary_elapsed = (period - 1) * PERIOD_LENGTH_SECONDS
            else:
                boundary_seconds_remaining = 0
                boundary_elapsed = REGULATION_SECONDS + (period - 5) * OT_LENGTH_SECONDS
            # Use the score *before* this event applied (period_start snapshot).
            boundary_score_home = int(row.score_home) if row.score_home is not None else score_home
            boundary_score_away = int(row.score_away) if row.score_away is not None else score_away
            # If this is the very first event of the game we want 0-0 at tip.
            if period == 1 and not points:
                boundary_score_home = 0
                boundary_score_away = 0
            boundary_diff = boundary_score_home - boundary_score_away
            boundary_wp = _logistic_wp_home(boundary_diff, boundary_seconds_remaining, None)
            points.append(
                WinProbPoint(
                    seconds_elapsed=boundary_elapsed,
                    score_home=boundary_score_home,
                    score_away=boundary_score_away,
                    wp_home=round(boundary_wp, 4),
                    event=None,
                )
            )
            prev_wp = boundary_wp

        if not _is_scoring_event(row.action_type, row.sub_type):
            continue

        # Use the team that scored as the possession arrow for the WP that
        # follows this play. Without team metadata we leave it neutral.
        wp = _logistic_wp_home(score_diff, seconds_remaining, None)
        prev_score_diff = (
            (points[-1].score_home - points[-1].score_away) if points else 0
        )
        label = None
        if prev_wp is not None:
            label = _swing_label(prev_wp, wp, prev_score_diff, score_diff, row.action_type)

        points.append(
            WinProbPoint(
                seconds_elapsed=seconds_elapsed,
                score_home=score_home,
                score_away=score_away,
                wp_home=round(wp, 4),
                event=label,
            )
        )
        prev_wp = wp

    return points


def compute_lead_tracker(db: Session, game_id: str) -> List[LeadPoint]:
    """Walk PBP once and emit one ``LeadPoint`` per minute boundary 0..N.

    Regular-length games yield 48 entries (minute 0 = tip, minute 47 = the
    final minute boundary before the buzzer). If the game went to overtime,
    the array is extended to cover the OT minutes (53 for 1OT, 58 for 2OT,
    etc.). The first entry is always ``minute=0, home_lead=0``.
    """
    rows = (
        db.query(PlayByPlay)
        .filter(PlayByPlay.game_id == game_id)
        .order_by(PlayByPlay.action_number.asc())
        .all()
    )
    if not rows:
        return []

    # Build a flat list of (seconds_elapsed, score_home, score_away) tuples.
    timeline: List[Tuple[int, int, int]] = []
    score_home = 0
    score_away = 0
    max_period = 1
    for row in rows:
        if row.score_home is not None:
            score_home = int(row.score_home)
        if row.score_away is not None:
            score_away = int(row.score_away)
        period = row.period or 1
        if period > max_period:
            max_period = period
        seconds_elapsed = _seconds_elapsed(period, row.clock)
        timeline.append((seconds_elapsed, score_home, score_away))

    # Determine total minutes covered. Regulation = 48. Each OT period adds 5.
    if max_period <= 4:
        total_minutes = 48
    else:
        ot_periods = max_period - 4
        total_minutes = 48 + ot_periods * 5

    # Emit minutes 0..(total_minutes - 1) inclusive so the array length matches
    # the spec: regulation -> 48 entries, 1OT -> 53, 2OT -> 58, etc.
    points: List[LeadPoint] = [LeadPoint(minute=0, home_lead=0)]
    cursor = 0
    last_home = 0
    last_away = 0
    for minute in range(1, total_minutes):
        boundary_seconds = minute * 60
        # Advance the cursor to the latest event at or before this boundary.
        while cursor < len(timeline) and timeline[cursor][0] <= boundary_seconds:
            _, last_home, last_away = timeline[cursor]
            cursor += 1
        points.append(LeadPoint(minute=minute, home_lead=last_home - last_away))
    return points
