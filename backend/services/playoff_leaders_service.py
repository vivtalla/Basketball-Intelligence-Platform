"""Sprint 77 — Playoff narrative leaders service.

Builds the small ranked-leaderboard payload that fills the playoff hero rail
on the home page. Each entry combines a player's headline scoring line with a
trend symbol (▲ / → / ▼) computed from recent playoff games and a 5-game
quality grade where each game is graded 1..5 against the player's own
season-average pts_pg.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import Player, PlayerGameLog, SeasonStat
from models.playoffs import PlayoffLeaderEntry


# Thresholds that bucket `last_3_avg - season_avg` into the trend glyph.
# Kept in points-per-game units. Small enough to be sensitive to a couple
# of strong/quiet playoff games, large enough to ignore noise.
_TREND_DELTA_UP = 2.0
_TREND_DELTA_DOWN = -2.0


def _format_line(row: SeasonStat) -> str:
    """Return a compact single-line summary like '31.4 PPG · 7.2 AST · 58.4 TS%'."""

    def _num(value: Optional[float], suffix: str, scale: float = 1.0, digits: int = 1) -> Optional[str]:
        if value is None:
            return None
        try:
            scaled = float(value) * scale
        except (TypeError, ValueError):
            return None
        return "{0:.{1}f} {2}".format(scaled, digits, suffix)

    parts: List[str] = []
    pts = _num(row.pts_pg, "PPG")
    if pts is not None:
        parts.append(pts)
    ast = _num(row.ast_pg, "AST")
    if ast is not None:
        parts.append(ast)
    ts = _num(row.ts_pct, "TS%", scale=100.0)
    if ts is not None:
        parts.append(ts)
    if not parts:
        return ""
    return " · ".join(parts)


def _trend_glyph(recent_pts: List[float], season_avg: Optional[float]) -> str:
    """Return ▲ / → / ▼ based on the delta between last-3-game pts and season avg."""
    if season_avg is None or not recent_pts:
        return "→"  # right arrow
    last_three = recent_pts[:3]
    if not last_three:
        return "→"
    avg_three = sum(last_three) / float(len(last_three))
    delta = avg_three - float(season_avg)
    if delta >= _TREND_DELTA_UP:
        return "▲"  # up triangle
    if delta <= _TREND_DELTA_DOWN:
        return "▼"  # down triangle
    return "→"


def _quintile_grade(value: float, sorted_values: List[float]) -> int:
    """Return a 1..5 grade where 5 = top quintile of the per-game distribution."""
    if not sorted_values:
        return 3
    n = len(sorted_values)
    # Count how many entries are < value (rank within distribution).
    below = sum(1 for v in sorted_values if v < value)
    # Percentile in [0, 1).
    pct = below / float(n)
    if pct >= 0.8:
        return 5
    if pct >= 0.6:
        return 4
    if pct >= 0.4:
        return 3
    if pct >= 0.2:
        return 2
    return 1


def _recent_grades(
    season_pts_history: List[float], recent_pts: List[float], limit: int = 5
) -> List[int]:
    """Grade the last ``limit`` games against the player's full season distribution.

    Each grade is 1..5 (top quintile = 5). When fewer than ``limit`` games are
    available, return only the grades we have so the caller sees the true
    sample size.
    """
    if not recent_pts:
        return []
    sorted_history = sorted(season_pts_history) if season_pts_history else sorted(recent_pts)
    return [_quintile_grade(pts, sorted_history) for pts in recent_pts[:limit]]


def compute_playoff_leaders(
    db: Session,
    season: str,
    limit: int = 5,
) -> List[PlayoffLeaderEntry]:
    """Top-N playoff scoring leaders with trend symbol and 5-game grade.

    Pulls SeasonStat rows where season=season AND is_playoff=True,
    sorted by pts_pg desc. For each player, computes:
        - rank (1..N)
        - player_name, team_abbreviation
        - line: "31.4 PPG · 7.2 AST · 58.4 TS%" (formatted from SeasonStat fields)
        - trend: "▲" / "→" / "▼" — based on (pts in last 3 playoff games) vs
          season average pts_pg.
        - recent_games_grade: List[int] of length up to 5, each 1-5 stars based
          on per-game performance vs season distribution.
    """
    if limit <= 0:
        return []

    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == True,  # noqa: E712
        )
        .order_by(SeasonStat.pts_pg.desc().nullslast())
        .all()
    )

    leaders: List[PlayoffLeaderEntry] = []
    rank = 0
    for row in rows:
        if row.pts_pg is None:
            continue
        rank += 1
        if rank > limit:
            break

        player = db.query(Player).filter(Player.id == row.player_id).first()
        player_name = player.full_name if player is not None and player.full_name else "Player {0}".format(row.player_id)

        history_rows = (
            db.query(PlayerGameLog)
            .filter(
                PlayerGameLog.player_id == row.player_id,
                PlayerGameLog.season == season,
                PlayerGameLog.season_type == "Playoffs",
            )
            .order_by(PlayerGameLog.game_date.desc().nullslast(), PlayerGameLog.game_id.desc())
            .all()
        )
        recent_pts: List[float] = [
            float(log.pts) for log in history_rows if log.pts is not None
        ]

        trend = _trend_glyph(recent_pts, row.pts_pg)
        grades = _recent_grades(recent_pts, recent_pts, limit=5)

        leaders.append(
            PlayoffLeaderEntry(
                rank=rank,
                player_id=int(row.player_id),
                player_name=player_name,
                team_abbreviation=row.team_abbreviation or "",
                line=_format_line(row),
                trend=trend,
                recent_games_grade=grades,
            )
        )

    return leaders


__all__ = ["compute_playoff_leaders"]
