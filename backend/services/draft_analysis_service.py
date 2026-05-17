"""Sprint 100 (Stream C) — high-level draft analysis.

Three public functions feed the enriched ``/api/draft/prospects/{id}``
response:

  * ``compute_projected_tier(db, prospect)`` — combines consensus rank,
    combine athleticism, and outcome-weighted comp distribution into a
    single tier label (``lottery`` | ``first_round`` | ``second_round`` |
    ``undrafted``).
  * ``compute_risk_indicators(db, prospect)`` — five 0..1 risk axes:
    age, sample, level (conference / league strength), athleticism,
    shooting. UI dims projections when any axis is high.
  * ``compute_historical_baseline(db, prospect)`` — derives the
    "prospects with this archetype became: X% star, Y% starter, …"
    distribution from the comp neighbourhood of historical outcomes.

``compute_team_fit`` is **deferred** to Sprint 101 — needs the team
archetype service threaded through; out-of-scope here.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import (
    DraftMockRanking, DraftOutcome, DraftProspect, DraftProspectStat,
)
from services.draft_outcome_classifier import tier_rank
from services.draft_prospect_comp_service_v2 import find_nba_comps_v2
from services.draft_translation_service_v2 import (
    _league_strength_key, LEAGUE_STRENGTH,
)

logger = logging.getLogger(__name__)


def _latest_stat(prospect: DraftProspect) -> Optional[DraftProspectStat]:
    rows = list(prospect.stats or [])
    if not rows:
        return None
    rows.sort(key=lambda r: (r.season or "", (r.gp or 0)), reverse=True)
    return rows[0]


# ── tier projection ──────────────────────────────────────────────────


def compute_projected_tier(
    db: Session,
    prospect: DraftProspect,
) -> str:
    """Return one of ``lottery`` | ``first_round`` | ``second_round`` | ``undrafted``.

    Strategy: consensus_rank_float is the strongest signal when present.
    Without that, fall back to the comp neighbourhood's median outcome
    tier. With neither, return ``"unknown"``.
    """
    rank = prospect.consensus_rank_float
    if rank is not None:
        if rank <= 14:
            return "lottery"
        if rank <= 30:
            return "first_round"
        if rank <= 60:
            return "second_round"
        return "undrafted"

    comps = find_nba_comps_v2(db, prospect.id, top_k=5)
    if not comps:
        return "unknown"
    tiers = [c.get("outcome_tier") for c in comps if c.get("outcome_tier")]
    if not tiers:
        return "second_round"  # weak default

    ranks = [tier_rank(t) for t in tiers]
    median = sorted(ranks)[len(ranks) // 2]
    if median >= 4:    # star / superstar median → lottery
        return "lottery"
    if median == 3:    # starter median → first_round
        return "first_round"
    if median == 2:    # role_player median → second_round
        return "second_round"
    return "undrafted"


# ── risk indicators ──────────────────────────────────────────────────


def _age_risk(age: Optional[float]) -> float:
    if age is None:
        return 0.5
    if age < 19:
        return 0.15
    if age < 20:
        return 0.25
    if age < 21:
        return 0.35
    if age < 22:
        return 0.55
    if age < 23:
        return 0.70
    return 0.85


def _sample_risk(stat: Optional[DraftProspectStat]) -> float:
    if stat is None or stat.gp is None:
        return 0.7
    gp = stat.gp
    if gp >= 30:
        return 0.15
    if gp >= 20:
        return 0.30
    if gp >= 12:
        return 0.55
    return 0.85


def _level_risk(prospect: DraftProspect, stat: Optional[DraftProspectStat]) -> float:
    if stat is None:
        return 0.6
    key = _league_strength_key(prospect.school, stat.league)
    strength = LEAGUE_STRENGTH.get(key, 0.85)
    # Map strength (0.7–1.12) → risk (0.05–0.85), inverted.
    risk = 1.0 - (strength - 0.7) / 0.5
    return round(max(0.05, min(0.95, risk)), 2)


def _athleticism_risk(prospect: DraftProspect) -> float:
    """Reads combine measurements (if any) to detect bottom-decile profiles."""
    measurements = list(prospect.measurements or [])
    if not measurements:
        return 0.5
    m = measurements[0]
    flags = 0
    checks = 0
    if m.wingspan is not None and prospect.height_inches:
        checks += 1
        # Negative wingspan-to-height differential is concerning.
        if m.wingspan < prospect.height_inches - 1.0:
            flags += 1
    if m.max_vert is not None:
        checks += 1
        if m.max_vert < 30:
            flags += 1
    if m.lane_agility_seconds is not None:
        checks += 1
        if m.lane_agility_seconds > 11.5:
            flags += 1
    if checks == 0:
        return 0.5
    return round(flags / checks, 2)


def _shooting_risk(stat: Optional[DraftProspectStat]) -> float:
    """Higher risk when the prospect doesn't shoot well at the college level."""
    if stat is None:
        return 0.5
    if stat.ts_pct is None and stat.fg3_pct is None:
        return 0.6
    ts_pct = stat.ts_pct or 0.55
    three = stat.fg3_pct or 0.33
    # Crude blend: TS% dominates, 3P% adds spice.
    score = 0.6 * (ts_pct - 0.50) / 0.20 + 0.4 * (three - 0.30) / 0.15
    # score in [0, ~1.5] when good; below 0 when poor. Convert to risk.
    risk = 1.0 - max(0.0, min(1.0, score))
    return round(risk, 2)


def compute_risk_indicators(db: Session, prospect: DraftProspect) -> Dict[str, float]:
    """Return five 0..1 risk indicators."""
    stat = _latest_stat(prospect)
    return {
        "age_risk": _age_risk(prospect.age_on_draft_day),
        "sample_risk": _sample_risk(stat),
        "level_risk": _level_risk(prospect, stat),
        "athleticism_risk": _athleticism_risk(prospect),
        "shooting_risk": _shooting_risk(stat),
    }


# ── historical baseline ──────────────────────────────────────────────


def compute_historical_baseline(
    db: Session,
    prospect: DraftProspect,
    top_k: int = 10,
) -> Dict[str, Any]:
    """Distribution of outcome tiers across the prospect's comp neighbourhood.

    Pulls the top-K comps (using v2 comp service), looks up each comp's
    historical outcome tier in ``draft_outcomes``, and returns the
    distribution as a dict::

        {
            "n_comps": 10,
            "n_with_outcome": 8,
            "star_pct": 0.25, "starter_pct": 0.50, "role_player_pct": 0.25,
            "bust_pct": 0.0,
        }

    When too few comps have outcomes recorded, returns a payload with
    ``n_with_outcome`` < 3 and ``insufficient: true`` so the API can
    surface the caveat.
    """
    comps = find_nba_comps_v2(db, prospect.id, top_k=top_k)
    if not comps:
        return {"n_comps": 0, "n_with_outcome": 0, "insufficient": True}

    counts = {"superstar": 0, "star": 0, "starter": 0, "role_player": 0, "bust": 0}
    n_with_outcome = 0
    for c in comps:
        tier = c.get("outcome_tier")
        if tier and tier in counts:
            counts[tier] += 1
            n_with_outcome += 1
    if n_with_outcome < 3:
        return {
            "n_comps": len(comps),
            "n_with_outcome": n_with_outcome,
            "insufficient": True,
            **{f"{k}_pct": 0.0 for k in counts},
        }
    out = {
        "n_comps": len(comps),
        "n_with_outcome": n_with_outcome,
        "insufficient": False,
        # Roll superstar into star for the consumer-facing baseline pct
        # so the four-bucket UI stays clean.
        "star_pct": round((counts["star"] + counts["superstar"]) / n_with_outcome, 3),
        "starter_pct": round(counts["starter"] / n_with_outcome, 3),
        "role_player_pct": round(counts["role_player"] / n_with_outcome, 3),
        "bust_pct": round(counts["bust"] / n_with_outcome, 3),
    }
    return out


def compute_team_fit(db: Session, prospect: DraftProspect) -> Optional[Dict[str, Any]]:
    """Deferred to Sprint 101 — needs team-archetype service integration."""
    return None
