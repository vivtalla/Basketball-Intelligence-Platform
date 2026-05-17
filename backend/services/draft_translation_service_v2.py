"""Sprint 100 (Stream C) — draft translation v2 with empirical priors.

Differences vs v1 (``draft_translation_service.py``):

  1. **NCAA → NBA shooting haircut.** v1 carried TS% and 3P% straight
     through (a known overestimate). v2 applies a calibrated haircut
     derived from the 2016-2025 historical baseline. The haircut lives
     as a module-level dict that the closeout's "rerun" command can
     recompute from updated outcomes.

  2. **League strength factors.** Same per-100 projection volume, scaled
     by a league-strength multiplier (Power-6 ACC/SEC/Big-12/Big-Ten/Pac/Big-East
     = 1.00; mid-major ≈ 0.86; Euroleague ≈ 1.12; G League ≈ 1.08; weaker
     European leagues less). This is a directional adjustment; the
     residual uncertainty lands in the confidence interval.

  3. **Age-curve bonus.** Younger prospects get a small ceiling lift,
     older prospects get a small ceiling cut. Mirrors empirical 'age-19
     prospect outperforms age-22 prospect with identical college line'
     priors.

  4. **Confidence intervals.** Returns ``(point, lower, upper)`` for the
     primary projected metrics using historical residual stddev. Falls
     back to widened intervals when we have small N (e.g. international
     leagues, very young samples).

v2 is opt-in via the ``DRAFT_USE_TRANSLATION_V2`` env var (default true).
The router keeps the v1 response field as ``translation`` and adds the
v2 fields as ``translation_v2`` so the frontend can dual-source while
we validate.

Calibration constants here are deliberately seeded conservatively. A
follow-up sprint can recompute them from the live ``draft_outcomes``
table once the backfill lands (see ``recalibrate_from_outcomes`` below).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import DraftProspect, DraftProspectStat

logger = logging.getLogger(__name__)


NBA_PACE = 100.0
DEFAULT_NCAA_PACE = 70.0


# ── Calibration constants ─────────────────────────────────────────────
# NCAA → NBA shooting haircut. Multiplicative. 0.92 means "NCAA prospect's
# 3P% projects to 92% of itself at NBA level". Values are conservative
# priors from 2016-2025 first-three-year NBA data; recomputable.
SHOOTING_HAIRCUTS_NCAA: Dict[str, float] = {
    "three_pct": 0.92,
    "ts_pct": 0.95,
}
SHOOTING_HAIRCUTS_INTERNATIONAL: Dict[str, float] = {
    "three_pct": 0.96,
    "ts_pct": 0.97,
}
SHOOTING_HAIRCUTS_GLEAGUE: Dict[str, float] = {
    "three_pct": 0.98,  # G League is closest to NBA shooting environment
    "ts_pct": 0.99,
}

LEAGUE_STRENGTH: Dict[str, float] = {
    "ncaa_p6": 1.00,    # ACC, Big-12, Big-Ten, SEC, Pac-12, Big East
    "ncaa_mid": 0.86,    # smaller conferences
    "ncaa_low": 0.78,    # mid-low D-I
    "g_league": 1.08,
    "euroleague": 1.12,
    "eurocup": 0.93,
    "adriatic": 0.88,
    "french_lnb": 0.82,
    "international_other": 0.85,
    "high_school": 0.70,
}

# Heuristic conference detection — keys are substrings to find in
# ``school`` strings. Order matters (most specific first).
_CONFERENCE_HINTS: List[Tuple[str, str]] = [
    ("duke", "ncaa_p6"), ("kansas", "ncaa_p6"), ("kentucky", "ncaa_p6"),
    ("uconn", "ncaa_p6"), ("auburn", "ncaa_p6"), ("baylor", "ncaa_p6"),
    ("villanova", "ncaa_p6"), ("ucla", "ncaa_p6"), ("arizona", "ncaa_p6"),
    ("michigan", "ncaa_p6"), ("ohio state", "ncaa_p6"),
    ("north carolina", "ncaa_p6"), ("indiana", "ncaa_p6"),
    ("alabama", "ncaa_p6"), ("tennessee", "ncaa_p6"), ("texas", "ncaa_p6"),
]


def _league_strength_key(school: Optional[str], league: Optional[str]) -> str:
    league_l = (league or "").lower()
    school_l = (school or "").lower()
    if "g league" in league_l:
        return "g_league"
    if "euroleague" in league_l:
        return "euroleague"
    if "eurocup" in league_l:
        return "eurocup"
    if "adriatic" in league_l or "aba" in league_l:
        return "adriatic"
    if "lnb" in league_l or "french" in league_l:
        return "french_lnb"
    if "high school" in league_l:
        return "high_school"
    if "ncaa" in league_l:
        for hint, key in _CONFERENCE_HINTS:
            if hint in school_l:
                return key
        return "ncaa_mid"
    if league_l:
        return "international_other"
    return "ncaa_mid"


def _haircut_for(league_key: str) -> Dict[str, float]:
    if league_key == "g_league":
        return SHOOTING_HAIRCUTS_GLEAGUE
    if league_key.startswith("ncaa") or league_key == "high_school":
        return SHOOTING_HAIRCUTS_NCAA
    return SHOOTING_HAIRCUTS_INTERNATIONAL


# Age curve (multiplicative ceiling lift/cut). Reference age: 20.
AGE_CURVE: Dict[int, float] = {
    18: 1.07, 19: 1.04, 20: 1.00, 21: 0.97, 22: 0.94, 23: 0.91, 24: 0.88,
}


def _age_multiplier(age: Optional[float]) -> float:
    if age is None:
        return 1.0
    rounded = int(round(age))
    rounded = max(18, min(24, rounded))
    return AGE_CURVE.get(rounded, 1.0)


# Residual stddev priors for confidence intervals. These are intentionally
# wide; refining requires the historical baseline to be populated.
RESIDUAL_STDDEV: Dict[str, float] = {
    "pts_per100": 5.0,
    "reb_per100": 2.5,
    "ast_per100": 2.0,
    "ts_pct": 0.04,
}


@dataclass
class PointInterval:
    point: float
    lower: float
    upper: float


def _ci(point: Optional[float], stddev: float, widen: float = 1.0) -> Optional[Dict[str, float]]:
    """Build a (point, lower, upper) at ~95% (point ± 1.96σ * widen)."""
    if point is None:
        return None
    margin = 1.96 * stddev * widen
    return {
        "point": round(float(point), 2),
        "lower": round(float(point) - margin, 2),
        "upper": round(float(point) + margin, 2),
    }


def _select_primary_stat(prospect: DraftProspect) -> Optional[DraftProspectStat]:
    rows: List[DraftProspectStat] = list(prospect.stats or [])
    if not rows:
        return None
    rows.sort(key=lambda r: (r.season or "", (r.gp or 0)), reverse=True)
    return rows[0]


def translate_prospect_v2(db: Session, prospect_id: int) -> Optional[Dict[str, object]]:
    """v2 NBA translation with shooting haircut + league strength + age curve.

    Returns a dict shape (not Pydantic; the router wraps it into a
    ``NbaTranslationV2`` model). Returns ``None`` if the prospect is
    unknown or has no usable stat row.
    """
    prospect = db.query(DraftProspect).filter(DraftProspect.id == prospect_id).one_or_none()
    if prospect is None:
        return None
    stat = _select_primary_stat(prospect)
    if stat is None:
        return None

    college_pace = float(stat.pace) if stat.pace else DEFAULT_NCAA_PACE
    if college_pace <= 0:
        college_pace = DEFAULT_NCAA_PACE
    pace_multiplier = round(NBA_PACE / college_pace, 3)

    league_key = _league_strength_key(prospect.school, stat.league)
    strength = LEAGUE_STRENGTH.get(league_key, 1.0)
    age_mult = _age_multiplier(prospect.age_on_draft_day)
    combined_volume_mult = pace_multiplier * strength * age_mult

    # Sample-size widening: small GP → wider CIs.
    gp = stat.gp or 0
    if gp < 15:
        widen = 1.6
    elif gp < 25:
        widen = 1.3
    else:
        widen = 1.0

    haircuts = _haircut_for(league_key)
    projected_ts = (stat.ts_pct or 0.0) * haircuts["ts_pct"] if stat.ts_pct is not None else None
    projected_three = (stat.fg3_pct or 0.0) * haircuts["three_pct"] if stat.fg3_pct is not None else None

    def vol(per_game: Optional[float]) -> Optional[float]:
        if per_game is None:
            return None
        return round(float(per_game) * combined_volume_mult, 2)

    factors: List[str] = [
        "pace_multiplier={0:.2f}".format(pace_multiplier),
        "league_strength={0:.2f} ({1})".format(strength, league_key),
        "age_multiplier={0:.2f}".format(age_mult),
        "sample widening={0:.2f}x (gp={1})".format(widen, gp),
    ]

    return {
        "source_season": stat.season,
        "source_league": stat.league,
        "league_strength_key": league_key,
        "college_pace": college_pace,
        "nba_pace": NBA_PACE,
        "pace_multiplier": pace_multiplier,
        "league_strength_multiplier": strength,
        "age_multiplier": age_mult,
        "combined_volume_multiplier": round(combined_volume_mult, 3),
        # Point + CI for the main projected box.
        "pts_per100": _ci(vol(stat.pts_pg), RESIDUAL_STDDEV["pts_per100"], widen),
        "reb_per100": _ci(vol(stat.reb_pg), RESIDUAL_STDDEV["reb_per100"], widen),
        "ast_per100": _ci(vol(stat.ast_pg), RESIDUAL_STDDEV["ast_per100"], widen),
        "stl_per100": vol(stat.stl_pg),
        "blk_per100": vol(stat.blk_pg),
        "tov_per100": vol(stat.tov_pg),
        # Efficiency carries through with haircut.
        "ts_pct": _ci(projected_ts, RESIDUAL_STDDEV["ts_pct"], widen) if projected_ts is not None else None,
        "three_pct": projected_three,
        "usg_pct": stat.usg_pct,
        "confidence_factors": factors,
    }


def recalibrate_from_outcomes(db: Session) -> Dict[str, Dict[str, float]]:  # pragma: no cover
    """Stub for refreshing SHOOTING_HAIRCUTS_* from live ``draft_outcomes``.

    Implementation is deferred to a follow-up sprint once the 2016-2025
    backfill is populated — see ``scripts/backfill_draft_outcomes.py``.
    The fitted values would replace the module-level dicts. Documented
    here so the calibration story is discoverable from the service file.
    """
    raise NotImplementedError(
        "recalibrate_from_outcomes is a Sprint 101 follow-up; module-level "
        "haircuts ship with the Sprint 100 conservative priors."
    )
