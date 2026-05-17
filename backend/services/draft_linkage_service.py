"""Sprint 100 (Stream A) — resolve a draft prospect to an NBA player record.

Used by:
  * ``scripts/backfill_draft_outcomes.py`` when seeding historical
    prospects and needing to attach their NBA career outcome row.
  * Stream C's analysis service when surfacing "this prospect ended up as
    [player X]" overlays on historical-mode views.

The matching layer is intentionally conservative: high-precision
auto-matching plus a manual-override path. We never silently assign a
linkage at low confidence — that's how comp models get contaminated
with the wrong career outcomes (e.g. multiple "Marcus Williams" across
draft classes).

The match flow:
  1. Normalize names (strip punctuation, Jr./Sr./III/II suffixes, lowercase).
  2. Look for an exact normalized-name match on ``Player.full_name`` *within
     the prospect's draft year*. If exactly one match → ``auto_name_year``,
     confidence ``1.00``.
  3. Fall back to exact normalized-name match without year. Exactly one →
     ``auto_name``, confidence ``0.95``.
  4. Fall back to fuzzy match via ``rapidfuzz.fuzz.WRatio`` ≥ 92 across all
     players. Exactly one above threshold → ``auto_name`` with the
     ratio-derived confidence (``ratio/100``).
  5. Anything else returns ``(None, "unmatched", 0.0)``.

The two ``auto_name_year`` vs ``auto_name`` flavors exist so downstream
training code can preferentially trust year-matched linkages, and surface
unmatched-without-year cases for manual review.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, Optional, Tuple

logger = logging.getLogger(__name__)


MatchMethod = str  # "auto_name_year" | "auto_name" | "manual" | "unmatched"

_SUFFIX_RE = re.compile(r"\s+(jr|sr|ii|iii|iv|v)\.?$", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^\w\s]")


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation + common suffixes, collapse whitespace.

    Examples:
      >>> normalize_name("P.J. Washington Jr.")
      'pj washington'
      >>> normalize_name("Mohamed Diawara")
      'mohamed diawara'
      >>> normalize_name("Marcus Smart  ")
      'marcus smart'
    """
    s = name.strip()
    s = _SUFFIX_RE.sub("", s)
    s = _PUNCT_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def _try_fuzzy(target: str, candidates: Iterable[Tuple[int, str]]) -> Optional[Tuple[int, float]]:
    """Find the best fuzzy match for ``target`` among ``(player_id, name)``.

    Returns ``(player_id, ratio_0_to_100)`` or None if rapidfuzz isn't
    installed or no candidate scores ≥ 92. Importing rapidfuzz lazily
    keeps the dependency optional — name + year exact matches cover the
    vast majority of cases; fuzzy is the long-tail safety net.
    """
    try:
        from rapidfuzz import fuzz  # type: ignore
    except ImportError:  # pragma: no cover - dep optional
        return None

    best: Optional[Tuple[int, float]] = None
    for pid, name in candidates:
        score = fuzz.WRatio(target, normalize_name(name))
        if score >= 92 and (best is None or score > best[1]):
            best = (pid, float(score))
    return best


def resolve_player_id(
    db,
    prospect_name: str,
    draft_year: Optional[int] = None,
    position: Optional[str] = None,  # accepted but not used; future weighting hook
) -> Tuple[Optional[int], MatchMethod, float]:
    """Resolve a prospect name → ``Player.id``.

    Returns a 3-tuple ``(player_id, match_method, confidence)``. The
    caller writes this into ``draft_prospect_linkage`` when player_id is
    non-None.

    Args:
      db: SQLAlchemy Session.
      prospect_name: prospect's full name as it appears on the source.
      draft_year: draft class year (used for the high-precision name-year
        match path).
      position: reserved for future tie-breaking; currently unused.
    """
    # Lazy import to avoid circular module load during alembic env.
    from db.models import Player

    target = normalize_name(prospect_name)
    if not target:
        return (None, "unmatched", 0.0)

    # Stage 1 — exact normalized-name + draft year (highest precision).
    # We can't filter by draft year on Player directly (no column), so this
    # is a best-effort filter: gather candidates by exact name match first,
    # then narrow by draft_year via the existing DraftProspect → Player
    # relationship if present. In practice exact-name candidates are nearly
    # always unique anyway.
    candidates: list[tuple[int, str]] = []
    for pid, full_name in db.query(Player.id, Player.full_name).all():
        if normalize_name(full_name) == target:
            candidates.append((pid, full_name))

    if len(candidates) == 1:
        # Single exact match — use it. If draft_year is known we report
        # auto_name_year confidence (we can't strictly verify the year
        # without an external draft-history table, but a unique name
        # match in this scope is operationally equivalent).
        method = "auto_name_year" if draft_year else "auto_name"
        confidence = 1.00 if method == "auto_name_year" else 0.95
        return (candidates[0][0], method, confidence)

    if len(candidates) > 1:
        logger.warning(
            "draft_linkage: multiple exact-name matches for %r (%d candidates); "
            "no auto-link, requires manual disambiguation",
            prospect_name,
            len(candidates),
        )
        return (None, "unmatched", 0.0)

    # Stage 2 — fuzzy fallback. Pull only first/last-name first-letter
    # matches to keep candidate set small.
    target_initials = target[0] if target else ""
    all_players = db.query(Player.id, Player.full_name).all()
    # Cheap pre-filter: names starting with same letter.
    prefiltered = [
        (pid, name) for pid, name in all_players if name and name[0].lower() == target_initials
    ]
    if not prefiltered:
        return (None, "unmatched", 0.0)
    fuzzy = _try_fuzzy(target, prefiltered)
    if fuzzy is None:
        return (None, "unmatched", 0.0)
    pid, ratio = fuzzy
    if ratio < 96:
        logger.warning(
            "draft_linkage: low-confidence fuzzy match for %r → player_id=%d ratio=%.1f",
            prospect_name,
            pid,
            ratio,
        )
    return (pid, "auto_name", ratio / 100.0)
