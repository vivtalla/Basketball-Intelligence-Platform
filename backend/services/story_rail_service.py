"""Sprint 77 — Story Rail service.

Auto-generates three data-driven story tiles for the broadsheet home page.
The tiles are computed from current playoff data — never editorial copy
— and always link to internal routes only (no external sports journalism
URLs, which would mix CourtVue UI with paywalled content).

Three tile slots, each computed independently so a missing slot degrades
to two tiles rather than failing the whole rail:

  1. Heat Check     — playoff player with the largest positive delta
                      between (avg pts in last 3 playoff games) and
                      season pts_pg. Frames the player as "trending up".
  2. Efficiency Desk — playoff player with the highest TS% among
                      qualified scorers (>=15 PPG, >=4 GP). Frames the
                      player as "scoring at a clip".
  3. X-Factor       — best playoff impact composite among non-headliners
                      (PPG < 22 to filter out the obvious top-5 names).
                      Frames a secondary scorer / playmaker as a hidden
                      driver.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy.orm import Session

from db.models import Player, PlayerGameLog, SeasonStat
from models.playoffs import PlayoffStoryTile
from services.playoff_leaders_service import _impact_score


_MIN_GAMES_FOR_TREND = 3
_MIN_GAMES_FOR_EFFICIENCY = 4
_MIN_PPG_FOR_EFFICIENCY = 15.0
_MAX_PPG_FOR_X_FACTOR = 22.0
_MIN_PPG_FOR_X_FACTOR = 8.0


def _player_name(db: Session, player_id: int) -> str:
    player = db.query(Player).filter(Player.id == player_id).first()
    if player is not None and player.full_name:
        return player.full_name
    return "Player {0}".format(player_id)


def _recent_pts(db: Session, player_id: int, season: str, limit: int = 3) -> List[float]:
    rows = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id == player_id,
            PlayerGameLog.season == season,
            PlayerGameLog.season_type == "Playoffs",
        )
        .order_by(PlayerGameLog.game_date.desc().nullslast(), PlayerGameLog.game_id.desc())
        .limit(limit)
        .all()
    )
    return [float(r.pts) for r in rows if r.pts is not None]


def _heat_check(db: Session, season: str, rows: List[SeasonStat]) -> Optional[PlayoffStoryTile]:
    """Find the biggest positive scoring trend in the last 3 playoff games."""
    best_delta: float = 0.0
    best_row: Optional[SeasonStat] = None
    best_recent: List[float] = []

    for row in rows:
        if row.pts_pg is None or row.pts_pg < 12.0:
            continue
        recent = _recent_pts(db, int(row.player_id), season, limit=_MIN_GAMES_FOR_TREND)
        if len(recent) < _MIN_GAMES_FOR_TREND:
            continue
        avg_recent = sum(recent) / len(recent)
        delta = avg_recent - float(row.pts_pg)
        if delta > best_delta:
            best_delta = delta
            best_row = row
            best_recent = recent

    if best_row is None or best_delta < 3.0:
        return None

    name = _player_name(db, int(best_row.player_id))
    last3 = ", ".join("{0:.0f}".format(p) for p in best_recent)
    headline = (
        "{name} is heating up: {avg:.1f} PPG over his last three "
        "({delta_sign}{delta:.1f} above season pace)."
    ).format(
        name=name,
        avg=sum(best_recent) / len(best_recent),
        delta_sign="+" if best_delta >= 0 else "",
        delta=best_delta,
    )
    subhead = "Last three games: {0} pts.".format(last3)

    return PlayoffStoryTile(
        kicker="Heat Check",
        headline=headline,
        subhead=subhead,
        href="/players/{0}".format(int(best_row.player_id)),
        read_time="Live · refreshes nightly",
    )


def _efficiency_desk(db: Session, rows: List[SeasonStat]) -> Optional[PlayoffStoryTile]:
    """Highest TS% among qualified playoff scorers."""
    best_ts: float = 0.0
    best_row: Optional[SeasonStat] = None

    for row in rows:
        if row.pts_pg is None or row.pts_pg < _MIN_PPG_FOR_EFFICIENCY:
            continue
        if row.gp is None or row.gp < _MIN_GAMES_FOR_EFFICIENCY:
            continue
        if row.ts_pct is None:
            continue
        ts = float(row.ts_pct) * 100.0
        if ts > best_ts:
            best_ts = ts
            best_row = row

    if best_row is None or best_ts < 55.0:
        return None

    name = _player_name(db, int(best_row.player_id))
    headline = (
        "{name} is scoring at a {ts:.1f} TS% clip — the most efficient "
        "high-volume bucket-getter of these playoffs."
    ).format(name=name, ts=best_ts)
    subhead = "{ppg:.1f} PPG on {gp} games, {team}.".format(
        ppg=float(best_row.pts_pg),
        gp=int(best_row.gp),
        team=best_row.team_abbreviation or "",
    )

    return PlayoffStoryTile(
        kicker="Efficiency Desk",
        headline=headline,
        subhead=subhead,
        href="/players/{0}".format(int(best_row.player_id)),
        read_time="Updated nightly",
    )


def _x_factor(db: Session, rows: List[SeasonStat]) -> Optional[PlayoffStoryTile]:
    """Highest impact composite among non-headline scorers."""
    candidates = [
        r for r in rows
        if r.pts_pg is not None
        and _MIN_PPG_FOR_X_FACTOR <= float(r.pts_pg) < _MAX_PPG_FOR_X_FACTOR
        and r.gp is not None and r.gp >= 3
    ]
    if not candidates:
        return None

    candidates.sort(key=_impact_score, reverse=True)
    best_row = candidates[0]
    score = _impact_score(best_row)
    if score < 8.0:
        return None

    name = _player_name(db, int(best_row.player_id))
    parts: List[str] = []
    if best_row.pts_pg is not None:
        parts.append("{0:.1f} PPG".format(float(best_row.pts_pg)))
    if best_row.ast_pg is not None and float(best_row.ast_pg) >= 4.0:
        parts.append("{0:.1f} AST".format(float(best_row.ast_pg)))
    if best_row.reb_pg is not None and float(best_row.reb_pg) >= 6.0:
        parts.append("{0:.1f} RPG".format(float(best_row.reb_pg)))
    if best_row.net_rating is not None and float(best_row.net_rating) >= 3.0:
        parts.append("+{0:.1f} NET".format(float(best_row.net_rating)))
    line = " · ".join(parts) if parts else "{0:.1f} PPG".format(float(best_row.pts_pg or 0))

    headline = (
        "{name} is the X-factor nobody's writing about — "
        "quietly tilting games for {team}."
    ).format(name=name, team=best_row.team_abbreviation or "his team")
    subhead = line

    return PlayoffStoryTile(
        kicker="X-Factor",
        headline=headline,
        subhead=subhead,
        href="/players/{0}".format(int(best_row.player_id)),
        read_time="Updated nightly",
    )


def compute_story_rail(db: Session, season: str) -> List[PlayoffStoryTile]:
    """Compute up to 3 auto-generated story tiles for the given season.

    Returns an empty list if no playoff data exists for the season. Each
    tile slot is computed independently — a slot that can't find a
    qualifying player is skipped rather than padded with placeholder copy.
    """
    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.season == season,
            SeasonStat.is_playoff == True,  # noqa: E712
        )
        .all()
    )
    if not rows:
        return []

    tiles: List[PlayoffStoryTile] = []
    for builder in (_heat_check, _efficiency_desk, _x_factor):
        try:
            if builder is _heat_check:
                tile = builder(db, season, rows)
            else:
                tile = builder(db, rows)
        except Exception:  # pragma: no cover — story tiles are best-effort
            tile = None
        if tile is not None:
            tiles.append(tile)
    return tiles


__all__ = ["compute_story_rail"]
