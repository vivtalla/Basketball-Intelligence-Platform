"""Sprint 100 (Stream A) — deterministic NBA career outcome classifier.

Used by:
  * ``scripts/backfill_draft_outcomes.py`` when seeding the 2016-2025
    historical baseline.
  * Stream C's ``draft_analysis_service`` when computing the historical
    baseline distribution for a prospect's comp neighbourhood.

Tiers are intentionally coarse — five buckets covering the full range from
"never really played" to "Hall of Fame trajectory" — because comp service
needs a stable, low-cardinality outcome label that doesn't require external
priors to interpret. Thresholds were chosen to roughly match the
distribution seen in 2016-2020 drafts (most players are role-player or
bust; star/superstar are explicitly rare).

Thresholds are calibrated to **career to date**, not single-season. The
caller is responsible for supplying valid cumulative numbers (None is
treated as zero — useful for "never played in NBA" cases).
"""

from __future__ import annotations

from typing import Literal, Optional

OutcomeTier = Literal["bust", "role_player", "starter", "star", "superstar"]


def _z(x: Optional[float]) -> float:
    return float(x) if x is not None else 0.0


def classify_outcome(
    career_games: Optional[int] = None,
    career_minutes: Optional[float] = None,
    career_ws: Optional[float] = None,
    all_star_selections: Optional[int] = None,
    all_nba_selections: Optional[int] = None,
) -> OutcomeTier:
    """Map a player's cumulative NBA career to a single tier label.

    Priority order — most specific wins:
      1. ``superstar`` — 3+ All-NBA selections (any team) OR 8+ All-Star
         selections.
      2. ``star`` — 1+ All-NBA selection OR 3+ All-Star selections.
      3. ``starter`` — 30+ career WS, 8000+ minutes (≈ 3 full starter
         seasons), no All-Star selections yet.
      4. ``role_player`` — 200+ career games OR 5+ career WS.
      5. ``bust`` — everything else.

    Args:
      career_games: total regular-season games played.
      career_minutes: total regular-season minutes played.
      career_ws: cumulative Basketball-Reference Win Shares.
      all_star_selections: All-Star team appearances.
      all_nba_selections: All-NBA (1st/2nd/3rd) team appearances.

    Returns:
      One of ``"bust" | "role_player" | "starter" | "star" | "superstar"``.
    """
    games = int(_z(career_games))
    minutes = _z(career_minutes)
    ws = _z(career_ws)
    all_star = int(_z(all_star_selections))
    all_nba = int(_z(all_nba_selections))

    if all_nba >= 3 or all_star >= 8:
        return "superstar"
    if all_nba >= 1 or all_star >= 3:
        return "star"
    if ws >= 30 and minutes >= 8000:
        return "starter"
    if games >= 200 or ws >= 5:
        return "role_player"
    return "bust"


# Tier ordering for sort + comparison (high → low).
TIER_RANK: dict[str, int] = {
    "superstar": 5,
    "star": 4,
    "starter": 3,
    "role_player": 2,
    "bust": 1,
}


def tier_rank(tier: Optional[str]) -> int:
    """Return numeric rank for a tier label (unknown → 0)."""
    if tier is None:
        return 0
    return TIER_RANK.get(tier, 0)
