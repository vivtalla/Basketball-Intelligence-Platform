"""Sprint 77 — Playoff narrative leaders service.

Builds the small ranked-leaderboard payload that fills the playoff hero rail
on the home page. Each entry combines a player's headline scoring line with a
trend symbol (▲ / → / ▼) computed from recent playoff games and a 5-game
quality grade where each game is graded 1..5 against the player's own
season-average pts_pg.

Ordering is by a composite "playoff impact" score that combines scoring,
playmaking, rebounding, shooting efficiency, and on-court team impact
(`pts_pg * 0.35 + ast_pg * 0.20 + reb_pg * 0.10 + min(ts_pct, 0.65) * 100 * 0.20 +
net_rating * 0.15`). The TS% term is clamped at 65% to prevent small-sample
inflation (a player who went 1/1 from the field shouldn't outrank a 30 PPG
star), and qualifying thresholds (GP ≥ 4, MIN ≥ 22, PPG ≥ 12) filter out
cup-of-coffee bench players whose tiny samples produce noisy net ratings
and shooting splits.

The single-line "stat line" for each row is built dynamically: the most
narratively distinctive trio of stats (always PPG, then either AST or REB
based on which is more elite, then efficiency / impact / usage) so a
playmaker reads as "29.1 PPG · 8.4 AST · 62.1 TS%" while a stretch big
reads as "24.6 PPG · 11.2 RPG · +9.4 NET".
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

# Qualifying thresholds for "narrative leader" status.
# Reason: small samples produce nonsense (e.g., a 1-min cameo with 1/1 FG
# generates a 150% TS% and a +50 net rating that dominate the composite).
# A leader should be a rotation player with a genuine playoff workload.
MIN_GAMES_PLAYED = 4       # at least one full series of evidence
MIN_MINUTES_PER_GAME = 22  # rotation player, not garbage time
MIN_POINTS_PER_GAME = 12   # meaningful scoring role

# TS% contribution cap. 65% TS is elite-historical; capping here prevents
# small-sample shooters (78%+ on 30 attempts) from drowning out a 30 PPG
# star whose TS% sits at a more typical 60%.
TS_PCT_CAP = 0.65


def _impact_score(row: SeasonStat) -> float:
    """Composite playoff impact score used for ranking.

    Weights chosen so each component contributes a comparable share at
    elite levels (30/10/12/65TS/+10 net → ~17.0 total). NULL components
    contribute zero rather than penalize, since SeasonStat fields are
    sparsely populated for early-round role players. The TS% term is
    clamped at TS_PCT_CAP (65%) so a tiny-sample shooter at 100% doesn't
    dominate the composite.
    """
    pts = float(row.pts_pg) if row.pts_pg is not None else 0.0
    ast = float(row.ast_pg) if row.ast_pg is not None else 0.0
    reb = float(row.reb_pg) if row.reb_pg is not None else 0.0
    raw_ts = float(row.ts_pct) if row.ts_pct is not None else 0.0
    ts = min(raw_ts, TS_PCT_CAP) * 100.0
    net = float(row.net_rating) if row.net_rating is not None else 0.0
    return pts * 0.35 + ast * 0.20 + reb * 0.10 + ts * 0.20 + net * 0.15


def _is_qualified(row: SeasonStat) -> bool:
    """Return True if the row meets the rotation-player floor."""
    if row.pts_pg is None or float(row.pts_pg) < MIN_POINTS_PER_GAME:
        return False
    if row.gp is None or int(row.gp) < MIN_GAMES_PLAYED:
        return False
    if row.min_pg is None or float(row.min_pg) < MIN_MINUTES_PER_GAME:
        return False
    return True


def _format_line(row: SeasonStat) -> str:
    """Return a 3-stat headline line tailored to the player's profile.

    Slot 1 is always PPG (the rail is a "leaders" hero, scoring is the lede).
    Slot 2 picks between AST and RPG based on which is more elite for the
    player. Slot 3 picks efficiency (TS%), team impact (NET), or usage (USG%)
    based on which best characterizes the player.
    """
    parts: List[str] = []

    # Slot 1 — PPG (always)
    if row.pts_pg is not None:
        parts.append("{0:.1f} PPG".format(float(row.pts_pg)))

    # Slot 2 — playmaking vs. board work
    ast = float(row.ast_pg) if row.ast_pg is not None else 0.0
    reb = float(row.reb_pg) if row.reb_pg is not None else 0.0
    if ast >= 5.0 and ast * 1.5 >= reb:
        parts.append("{0:.1f} AST".format(ast))
    elif reb >= 6.0:
        parts.append("{0:.1f} RPG".format(reb))
    elif ast > 0 or reb > 0:
        if ast >= reb:
            parts.append("{0:.1f} AST".format(ast))
        else:
            parts.append("{0:.1f} RPG".format(reb))

    # Slot 3 — efficiency, impact, or usage (in priority order)
    ts = float(row.ts_pct) * 100.0 if row.ts_pct is not None else None
    net = float(row.net_rating) if row.net_rating is not None else None
    usg = float(row.usg_pct) if row.usg_pct is not None else None
    if ts is not None and ts >= 58.0:
        parts.append("{0:.1f} TS%".format(ts))
    elif net is not None and net >= 5.0:
        parts.append("+{0:.1f} NET".format(net))
    elif usg is not None and usg >= 28.0:
        parts.append("{0:.1f} USG%".format(usg))
    elif ts is not None and ts > 0:
        parts.append("{0:.1f} TS%".format(ts))
    elif net is not None:
        sign = "+" if net >= 0 else ""
        parts.append("{0}{1:.1f} NET".format(sign, net))

    return " · ".join(parts) if parts else ""


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
    """Top-N playoff impact leaders with trend symbol and 5-game grade.

    Pulls SeasonStat rows where season=season AND is_playoff=True, then
    ranks by `_impact_score(row)` (composite of scoring, playmaking,
    rebounding, shooting efficiency, and team net rating). For each
    player, computes:
        - rank (1..N) by composite impact score
        - player_name, team_abbreviation
        - line: dynamic 3-stat headline (see `_format_line`)
        - trend: "▲" / "→" / "▼" — based on (pts in last 3 playoff games) vs
          season average pts_pg.
        - recent_games_grade: List[int] of length up to 5, each 1-5 stars
          based on per-game performance vs season distribution.
    """
    if limit <= 0:
        return []

    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == True,  # noqa: E712
        )
        .all()
    )

    # Apply qualifying thresholds (rotation player, real workload) and rank
    # by composite impact score. If no players qualify (very early in the
    # postseason), fall back to the loose filter so the rail is never empty.
    qualified = [r for r in rows if _is_qualified(r)]
    if not qualified:
        qualified = [r for r in rows if r.pts_pg is not None]
    qualified.sort(key=_impact_score, reverse=True)

    leaders: List[PlayoffLeaderEntry] = []
    for rank, row in enumerate(qualified[:limit], start=1):
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
                impact_score=round(_impact_score(row), 1),
            )
        )

    return leaders


__all__ = ["compute_playoff_leaders"]
