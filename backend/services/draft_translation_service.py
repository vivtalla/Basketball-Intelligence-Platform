"""Sprint 78 / FO3 — pre-NBA → NBA stat translation.

Takes a draft prospect's most-recent pre-NBA season line and projects it
onto an NBA per-100-possessions line using:

1. Pace adjustment — NCAA ≈ 70 pos / 40 min; NBA ≈ 100 pos / 48 min. The
   ratio (`pace_multiplier`) scales raw per-game counts directly. Per-game
   numbers carry both volume and rate signal because GP and minutes are
   relatively similar; translating per-100 is the cleanest way to compare
   to NBA box totals.
2. Per-game ➜ per-100 — per-game stats are scaled by the pace multiplier.
   In effect, this normalizes for the "fewer trips per game" gap between
   college (40-min, ~70 pos) and the NBA (48-min, ~100 pos).
3. Efficiency carry — rate stats (ts_pct, usg_pct) carry through unchanged
   because they're already pace-independent. The translation service does
   *not* apply a hand-tuned NCAA-to-NBA shooting haircut: those era/role
   adjustments are an Sprint-79 deliverable when we wire empirical priors.

The returned `translation_confidence` is a 0..1 heuristic from three
signals (each ±0.2 against a baseline of 0.6):

- sample size (gp): full college season ≥ 25 ⇒ +0.1, < 15 ⇒ -0.2
- league strength (NCAA / G League / international): NCAA = +0.1,
  G League = +0.0, international ≈ 0.0 (Euroleague pace varies).
- pace multiplier sanity: a multiplier outside [1.1, 1.6] is penalized.

The output is meant to be a directional projection consumers can read
alongside raw per-game stats — not a forecast.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import DraftProspect, DraftProspectStat
from models.draft import NbaTranslation

logger = logging.getLogger(__name__)

NBA_PACE = 100.0
DEFAULT_NCAA_PACE = 70.0


def _select_primary_stat(prospect: DraftProspect) -> Optional[DraftProspectStat]:
    """Pick the most-recent stat row for translation.

    Sorts by season descending; if ties, the highest-GP row wins so we
    favor a meaningful sample over a partial transfer/redshirt season.
    """
    rows: List[DraftProspectStat] = list(prospect.stats or [])
    if not rows:
        return None
    rows.sort(key=lambda r: (r.season or "", (r.gp or 0)), reverse=True)
    return rows[0]


def _confidence(stat: DraftProspectStat, pace_multiplier: float) -> tuple[float, List[str]]:
    base = 0.6
    factors: List[str] = []

    gp = stat.gp or 0
    if gp >= 25:
        base += 0.1
        factors.append(f"sample size ok (gp={gp})")
    elif gp < 15:
        base -= 0.2
        factors.append(f"thin sample (gp={gp})")
    else:
        factors.append(f"sample size acceptable (gp={gp})")

    league = (stat.league or "").lower()
    if "ncaa" in league:
        base += 0.1
        factors.append("NCAA D-I league strength")
    elif "g league" in league:
        factors.append("G League — translation already near NBA pace")
    elif "high school" in league:
        base -= 0.2
        factors.append("high-school sample (low translation confidence)")
    else:
        factors.append("international league — pace varies")

    if pace_multiplier < 1.1 or pace_multiplier > 1.6:
        base -= 0.1
        factors.append(f"unusual pace ratio ({pace_multiplier:.2f})")

    return max(0.0, min(1.0, round(base, 3))), factors


def _scale(val: Optional[float], mult: float) -> Optional[float]:
    if val is None:
        return None
    return round(float(val) * mult, 2)


def translate_prospect_to_nba(db: Session, prospect_id: int) -> Optional[NbaTranslation]:
    """Translate a prospect's most-recent pre-NBA season into an NBA per-100 projection.

    Returns ``None`` if the prospect is unknown or has no usable stat row.
    """
    prospect: Optional[DraftProspect] = db.query(DraftProspect).filter(
        DraftProspect.id == prospect_id
    ).one_or_none()
    if prospect is None:
        return None

    stat = _select_primary_stat(prospect)
    if stat is None:
        return None

    college_pace = float(stat.pace) if stat.pace else DEFAULT_NCAA_PACE
    if college_pace <= 0:
        college_pace = DEFAULT_NCAA_PACE
    pace_multiplier = round(NBA_PACE / college_pace, 3)

    confidence, factors = _confidence(stat, pace_multiplier)

    return NbaTranslation(
        source_season=stat.season,
        source_league=stat.league,
        college_pace=college_pace,
        nba_pace=NBA_PACE,
        pace_multiplier=pace_multiplier,
        projected_pts_per100=_scale(stat.pts_pg, pace_multiplier),
        projected_reb_per100=_scale(stat.reb_pg, pace_multiplier),
        projected_ast_per100=_scale(stat.ast_pg, pace_multiplier),
        projected_stl_per100=_scale(stat.stl_pg, pace_multiplier),
        projected_blk_per100=_scale(stat.blk_pg, pace_multiplier),
        projected_tov_per100=_scale(stat.tov_pg, pace_multiplier),
        projected_ts_pct=stat.ts_pct,
        projected_usg_pct=stat.usg_pct,
        translation_confidence=confidence,
        confidence_factors=factors,
    )
