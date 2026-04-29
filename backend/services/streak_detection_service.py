"""Sprint 78 CF5 — Active streak detection service.

Walks ``PlayerGameLog`` in reverse-chronological order per player and counts
consecutive games meeting one of five criteria:

- ``30plus_pts``        — pts >= 30
- ``double_double``     — at least two of (pts, reb, ast) at 10+
- ``triple_double``     — pts, reb, ast all 10+
- ``50pct_fg_15fga``    — fg_pct >= 0.50 with fga >= 15
- ``5plus_3pm``         — fg3m >= 5

A streak is "active" when the most-recent game in the player's log meets
the criterion. As soon as we hit a non-qualifying game walking backwards,
the streak ends and we record its length.

``compute_active_streaks(db, season)`` runs the full league-wide refresh
and UPSERTS into ``player_streaks``. The caller (CLI / cron) commits.

Service notes:
- Only games with ``season_type`` "Regular Season" or "Playoffs" are
  considered. Pre-season / All-Star games are excluded because they're
  not part of the canonical streak narrative.
- Players with no recent games are skipped — we never write a length-0
  row, so the table only contains active streaks.
- The criterion threshold is stored verbatim on the row so a UI can render
  "≥30 pts" without consulting this module.
"""
from __future__ import annotations

import logging
from datetime import date as _date
from typing import Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import Player, PlayerGameLog, PlayerStreak, Team


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Streak definitions. Each is a (key, label, predicate, threshold-dict).
# Predicates take a PlayerGameLog row and return True if it qualifies.
# ---------------------------------------------------------------------------


def _is_30plus_pts(log: PlayerGameLog) -> bool:
    return log.pts is not None and int(log.pts) >= 30


def _is_double_double(log: PlayerGameLog) -> bool:
    pts = int(log.pts or 0)
    reb = int(log.reb or 0)
    ast = int(log.ast or 0)
    # Standard double-double = any two of pts/reb/ast at 10+.
    # We deliberately don't include blocks/steals here because the
    # "narrative" double-double is the scoring/playmaking/boards version.
    qualifying = sum(1 for v in (pts, reb, ast) if v >= 10)
    return qualifying >= 2


def _is_triple_double(log: PlayerGameLog) -> bool:
    return all(
        v is not None and int(v) >= 10
        for v in (log.pts, log.reb, log.ast)
    )


def _is_50pct_fg_15fga(log: PlayerGameLog) -> bool:
    if log.fga is None or int(log.fga) < 15:
        return False
    if log.fg_pct is None:
        return False
    return float(log.fg_pct) >= 0.50


def _is_5plus_3pm(log: PlayerGameLog) -> bool:
    return log.fg3m is not None and int(log.fg3m) >= 5


# Each entry: (streak_type_key, display_label, predicate, threshold_payload)
StreakDef = Tuple[str, str, Callable[[PlayerGameLog], bool], Dict[str, object]]

STREAK_DEFINITIONS: List[StreakDef] = [
    ("30plus_pts", "30+ point games", _is_30plus_pts, {"pts_ge": 30}),
    ("double_double", "double-doubles", _is_double_double, {"any_two_ge_10": ["pts", "reb", "ast"]}),
    ("triple_double", "triple-doubles", _is_triple_double, {"pts_ge": 10, "reb_ge": 10, "ast_ge": 10}),
    ("50pct_fg_15fga", "50%+ FG (15+ FGA)", _is_50pct_fg_15fga, {"fg_pct_ge": 0.50, "fga_ge": 15}),
    ("5plus_3pm", "5+ three-pointers", _is_5plus_3pm, {"fg3m_ge": 5}),
]


# Streak-type → label map for read-side translation. Surface in the API.
STREAK_LABELS: Dict[str, str] = {key: label for key, label, _pred, _thresh in STREAK_DEFINITIONS}


_VALID_SEASON_TYPES = ("Regular Season", "Playoffs")


def _player_logs_desc(db: Session, player_id: int) -> List[PlayerGameLog]:
    """All eligible game logs for a player, most-recent first."""
    return (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id == player_id,
            PlayerGameLog.season_type.in_(_VALID_SEASON_TYPES),
        )
        .order_by(
            PlayerGameLog.game_date.desc().nullslast(),
            PlayerGameLog.game_id.desc(),
        )
        .all()
    )


def _detect_streak(
    logs_desc: List[PlayerGameLog],
    predicate: Callable[[PlayerGameLog], bool],
) -> Optional[Dict[str, object]]:
    """Return streak metadata if the player's most-recent game qualifies.

    Walks ``logs_desc`` (already most-recent first). If the very first
    log fails the predicate, the streak is not active and we return None.
    Otherwise we count consecutive qualifying games until we hit a miss
    or run out of logs, then return ``{length, started_on, last_game_on,
    last_game_id, season}``.
    """
    if not logs_desc:
        return None

    head = logs_desc[0]
    if not predicate(head):
        return None

    length = 0
    started_on: Optional[_date] = None
    for log in logs_desc:
        if not predicate(log):
            break
        length += 1
        started_on = log.game_date  # last assigned wins (oldest qualifying game)

    if length <= 0:
        return None

    return {
        "length": length,
        "started_on": started_on,
        "last_game_on": head.game_date,
        "last_game_id": head.game_id,
        "season": head.season,
    }


def _upsert_streak(
    db: Session,
    player_id: int,
    streak_type: str,
    threshold: Dict[str, object],
    detection: Dict[str, object],
) -> PlayerStreak:
    """Insert-or-update a single ``PlayerStreak`` row."""
    row = (
        db.query(PlayerStreak)
        .filter(
            PlayerStreak.player_id == player_id,
            PlayerStreak.streak_type == streak_type,
        )
        .first()
    )
    if row is None:
        row = PlayerStreak(
            player_id=player_id,
            streak_type=streak_type,
            length=int(detection["length"]),
            started_on=detection.get("started_on"),
            last_game_on=detection.get("last_game_on"),
            last_game_id=detection.get("last_game_id"),
            threshold=threshold,
            is_active=True,
            season=detection.get("season"),
        )
        db.add(row)
    else:
        row.length = int(detection["length"])
        row.started_on = detection.get("started_on")
        row.last_game_on = detection.get("last_game_on")
        row.last_game_id = detection.get("last_game_id")
        row.threshold = threshold
        row.is_active = True
        row.season = detection.get("season")
    return row


def _delete_inactive_streak(db: Session, player_id: int, streak_type: str) -> None:
    """Drop the row when a previously-active streak no longer holds.

    We delete rather than flip ``is_active`` to keep the table small and
    queries simple — the "active streaks" board is a snapshot, not a
    history log.
    """
    (
        db.query(PlayerStreak)
        .filter(
            PlayerStreak.player_id == player_id,
            PlayerStreak.streak_type == streak_type,
        )
        .delete(synchronize_session=False)
    )


def compute_player_streaks(db: Session, player_id: int) -> List[PlayerStreak]:
    """Recompute all five streak types for a single player.

    Writes UPSERTs but does **not** commit — the caller owns the txn so
    bulk runs can batch many players per commit.
    """
    logs_desc = _player_logs_desc(db, player_id)

    written: List[PlayerStreak] = []
    for streak_type, _label, predicate, threshold in STREAK_DEFINITIONS:
        detection = _detect_streak(logs_desc, predicate)
        if detection is None:
            _delete_inactive_streak(db, player_id, streak_type)
            continue
        row = _upsert_streak(
            db,
            player_id=player_id,
            streak_type=streak_type,
            threshold=threshold,
            detection=detection,
        )
        written.append(row)
    return written


def compute_active_streaks(db: Session, season: Optional[str] = None) -> Dict[str, int]:
    """Recompute active streaks for every player with at least one log row.

    Args:
        db: SQLAlchemy session.
        season: Optional. When provided, only players who logged at least
            one game in this season are recomputed; their full history is
            still used for streak detection. When None, every player with
            any logged game is processed.

    Returns:
        ``{"players_processed": int, "streaks_written": int}``.
    """
    if season:
        player_ids = [
            pid for (pid,) in db.query(PlayerGameLog.player_id)
            .filter(PlayerGameLog.season == season)
            .distinct()
            .all()
        ]
    else:
        player_ids = [
            pid for (pid,) in db.query(PlayerGameLog.player_id).distinct().all()
        ]

    streaks_written = 0
    for pid in player_ids:
        rows = compute_player_streaks(db, int(pid))
        streaks_written += len(rows)

    return {
        "players_processed": len(player_ids),
        "streaks_written": streaks_written,
    }


def fetch_top_active_streaks(
    db: Session,
    season: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, object]]:
    """Fetch the longest active streaks for the league-wide board.

    Returns a list of dicts (rather than ORM rows) so the caller can
    materialize them straight into the response model without a second
    join. Sorted by ``length`` descending. Streak rows with length < 2
    are filtered out — a "streak" of one is just a game.
    """
    query = (
        db.query(PlayerStreak, Player, Team)
        .join(Player, Player.id == PlayerStreak.player_id)
        .outerjoin(Team, Team.id == Player.team_id)
        .filter(PlayerStreak.length >= 2)
        .filter(PlayerStreak.is_active == True)  # noqa: E712
    )
    if season:
        query = query.filter(PlayerStreak.season == season)
    query = query.order_by(PlayerStreak.length.desc(), PlayerStreak.last_game_on.desc().nullslast())

    out: List[Dict[str, object]] = []
    for streak, player, team in query.limit(limit).all():
        out.append({
            "player_id": int(streak.player_id),
            "player_name": player.full_name if player and player.full_name else "Player {0}".format(streak.player_id),
            "team_abbreviation": (team.abbreviation if team else "") or "",
            "streak_type": streak.streak_type,
            "streak_label": STREAK_LABELS.get(streak.streak_type, streak.streak_type),
            "length": int(streak.length),
            "started_on": streak.started_on,
            "last_game_on": streak.last_game_on,
            "last_game_id": streak.last_game_id,
            "season": streak.season,
        })
    return out


def fetch_player_longest_active_streak(
    db: Session,
    player_id: int,
) -> Optional[Dict[str, object]]:
    """Return the player's longest active streak, or None if they have none.

    Used by the player-profile chip — we only show one chip per player
    even if multiple streaks are active.
    """
    streak = (
        db.query(PlayerStreak)
        .filter(
            PlayerStreak.player_id == player_id,
            PlayerStreak.is_active == True,  # noqa: E712
            PlayerStreak.length >= 2,
        )
        .order_by(PlayerStreak.length.desc(), PlayerStreak.last_game_on.desc().nullslast())
        .first()
    )
    if streak is None:
        return None
    return {
        "streak_type": streak.streak_type,
        "streak_label": STREAK_LABELS.get(streak.streak_type, streak.streak_type),
        "length": int(streak.length),
        "last_game_on": streak.last_game_on,
    }


__all__ = [
    "STREAK_DEFINITIONS",
    "STREAK_LABELS",
    "compute_active_streaks",
    "compute_player_streaks",
    "fetch_player_longest_active_streak",
    "fetch_top_active_streaks",
]
