"""Sprint 78 CF5 — Signature performance detection.

For each player's most-recent box-score line, ranks the line against the
player's own full career game-log distribution. Returns the top N "signature"
lines from the league's most recent slate.

Composite scoring formula (chosen for narrative recognizability — not a
predictive metric):

    composite = pts + 1.2 * reb + 1.5 * ast + 2.0 * stl + 2.0 * blk

Tiers:
- ``career``    — top 5% of the player's own career composite distribution
- ``signature`` — top 10% (and not already "career")

Why a percentile instead of an absolute threshold? Absolute lines look
different per archetype: a 38-point game is routine for Doncic but a
career night for Mikal Bridges. Percentile-of-self captures the "did this
player just have a personal-record-level game?" question directly.

Service notes:
- Career distribution sample size matters: with fewer than 20 logged games
  we can't reliably percentile-rank, so those players are excluded.
- The default "last completed game date" is the most-recent game-date that
  exists in ``PlayerGameLog`` regardless of season type, which keeps the
  feed working through the playoff window.
"""
from __future__ import annotations

import logging
from datetime import date as _date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, PlayerGameLog, Team


logger = logging.getLogger(__name__)


# Minimum games needed to compute a meaningful career percentile.
MIN_CAREER_GAMES = 20

# Tier thresholds (percentile of career distribution).
CAREER_TIER_PERCENTILE = 95.0    # top 5% of career games
SIGNATURE_TIER_PERCENTILE = 90.0  # top 10% of career games


def _composite(log: PlayerGameLog) -> float:
    pts = float(log.pts or 0)
    reb = float(log.reb or 0)
    ast = float(log.ast or 0)
    stl = float(log.stl or 0)
    blk = float(log.blk or 0)
    return pts + 1.2 * reb + 1.5 * ast + 2.0 * stl + 2.0 * blk


def _percentile_rank(value: float, distribution: List[float]) -> float:
    """Return percentile in [0, 100]. ``value`` is included in distribution."""
    if not distribution:
        return 0.0
    n = len(distribution)
    below = sum(1 for v in distribution if v < value)
    return (below / float(n)) * 100.0


def _format_line(log: PlayerGameLog) -> str:
    """Compact slash-line summary, e.g. '38/9/7'."""
    return "{0}/{1}/{2}".format(int(log.pts or 0), int(log.reb or 0), int(log.ast or 0))


def _last_completed_game_date(db: Session) -> Optional[_date]:
    """Return the most-recent ``game_date`` present in ``PlayerGameLog``."""
    row = (
        db.query(PlayerGameLog.game_date)
        .filter(PlayerGameLog.game_date.isnot(None))
        .order_by(PlayerGameLog.game_date.desc())
        .first()
    )
    if row is None:
        return None
    return row[0]


def compute_signature_performances(
    db: Session,
    target_date: Optional[_date] = None,
    limit: int = 10,
) -> List[Dict[str, object]]:
    """Return signature performances from a date's slate.

    Args:
        db: SQLAlchemy session.
        target_date: Game date to scan. When None, defaults to the last
            completed game date in the database.
        limit: Maximum number of signature lines returned, sorted by
            composite percentile descending.

    Returns:
        List of dicts shaped for ``SignaturePerformance``. Returns an
        empty list when no game logs exist for the date or when no
        player on that date qualifies for a tier.
    """
    if target_date is None:
        target_date = _last_completed_game_date(db)
    if target_date is None:
        return []

    # Pull every game log on the target date — one player per log.
    todays_logs = (
        db.query(PlayerGameLog)
        .filter(PlayerGameLog.game_date == target_date)
        .all()
    )
    if not todays_logs:
        return []

    candidates: List[Tuple[float, float, str, PlayerGameLog]] = []
    # (composite_score, career_percentile, tier, log)

    # For each player who played, pull their full career composite
    # distribution exactly once (avoid N+1 by caching per player_id).
    player_distributions: Dict[int, List[float]] = {}

    for log in todays_logs:
        player_id = int(log.player_id)
        if player_id not in player_distributions:
            history = (
                db.query(PlayerGameLog)
                .filter(PlayerGameLog.player_id == player_id)
                .all()
            )
            player_distributions[player_id] = [_composite(h) for h in history]

        career = player_distributions[player_id]
        if len(career) < MIN_CAREER_GAMES:
            continue

        score = _composite(log)
        pct = _percentile_rank(score, career)

        if pct >= CAREER_TIER_PERCENTILE:
            tier = "career"
        elif pct >= SIGNATURE_TIER_PERCENTILE:
            tier = "signature"
        else:
            continue

        candidates.append((score, pct, tier, log))

    # Sort by percentile desc — career nights ahead of signature ones,
    # ties broken by absolute composite.
    candidates.sort(key=lambda t: (t[1], t[0]), reverse=True)

    out: List[Dict[str, object]] = []
    for _score, pct, tier, log in candidates[:limit]:
        player = db.query(Player).filter(Player.id == log.player_id).first()
        team = (
            db.query(Team).filter(Team.id == player.team_id).first()
            if player and player.team_id is not None
            else None
        )
        out.append({
            "player_id": int(log.player_id),
            "player_name": player.full_name if player and player.full_name else "Player {0}".format(log.player_id),
            "team_abbreviation": (team.abbreviation if team else None),
            "game_id": log.game_id,
            "game_date": log.game_date,
            "matchup": log.matchup,
            "pts": int(log.pts or 0),
            "reb": int(log.reb or 0),
            "ast": int(log.ast or 0),
            "stl": int(log.stl or 0),
            "blk": int(log.blk or 0),
            "fgm": int(log.fgm or 0),
            "fga": int(log.fga or 0),
            "fg3m": int(log.fg3m or 0),
            "composite_score": round(_composite(log), 2),
            "career_percentile": round(pct, 1),
            "tier": tier,
            "line": _format_line(log),
        })
    return out


__all__ = [
    "MIN_CAREER_GAMES",
    "CAREER_TIER_PERCENTILE",
    "SIGNATURE_TIER_PERCENTILE",
    "compute_signature_performances",
]
