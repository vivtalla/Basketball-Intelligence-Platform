"""Sprint 78 CF5 — Career milestone proximity service.

Computes which career milestones each active player is approaching, with
an estimated games-to-milestone derived from their current-season per-game
pace. UPSERTs into ``milestone_snapshots``.

Career-total milestones tracked:

- Points:    10,000 / 15,000 / 20,000 / 25,000 / 30,000
- 3PM:       1,000 / 2,000 / 3,000
- Assists:   5,000 / 10,000
- Rebounds:  5,000 / 10,000

Career totals are derived from ``SeasonStat`` rows with ``is_playoff=False``
(regular-season totals are the canonical narrative for "10k career points",
not playoff-inclusive figures).

For each player, the service computes the next unhit threshold per family
(pts, fg3m, ast, reb), estimates games-to-go from this season's pace, and
writes a snapshot row. Already-hit milestones are recorded with
``games_to_milestone=None`` and ``achieved_on`` populated when we can
locate the box-score game where the threshold was crossed (best-effort —
falls back to None if there's no PlayerGameLog evidence).
"""
from __future__ import annotations

import logging
import math
from datetime import date as _date
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from db.models import (
    MilestoneSnapshot,
    Player,
    PlayerGameLog,
    SeasonStat,
    Team,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Milestone catalogue. Each entry: (key, label, stat-family, threshold).
# ``stat_family`` selects the SeasonStat aggregate column.
# ---------------------------------------------------------------------------

PTS_THRESHOLDS = [10_000, 15_000, 20_000, 25_000, 30_000]
THREE_PM_THRESHOLDS = [1_000, 2_000, 3_000]
AST_THRESHOLDS = [5_000, 10_000]
REB_THRESHOLDS = [5_000, 10_000]


def _format_threshold(threshold: int) -> str:
    if threshold >= 1000:
        return "{:,}".format(threshold)
    return str(threshold)


def _milestone_label(family: str, threshold: int) -> str:
    formatted = _format_threshold(threshold)
    if family == "pts":
        return "{0} career points".format(formatted)
    if family == "fg3m":
        return "{0} career 3-pointers".format(formatted)
    if family == "ast":
        return "{0} career assists".format(formatted)
    if family == "reb":
        return "{0} career rebounds".format(formatted)
    return "{0} career {1}".format(formatted, family)


def _milestone_key(family: str, threshold: int) -> str:
    """Stable key, e.g. (pts, 10000) → '10k_pts'."""
    if threshold >= 1000:
        head = "{0}k".format(threshold // 1000)
    else:
        head = str(threshold)
    return "{0}_{1}".format(head, family)


def _milestone_catalogue() -> List[Tuple[str, str, int, str]]:
    """Return the full ordered list of (key, family, threshold, label)."""
    out: List[Tuple[str, str, int, str]] = []
    for fam, thresholds in (
        ("pts", PTS_THRESHOLDS),
        ("fg3m", THREE_PM_THRESHOLDS),
        ("ast", AST_THRESHOLDS),
        ("reb", REB_THRESHOLDS),
    ):
        for thresh in thresholds:
            key = _milestone_key(fam, thresh)
            out.append((key, fam, thresh, _milestone_label(fam, thresh)))
    return out


MILESTONE_CATALOGUE: List[Tuple[str, str, int, str]] = _milestone_catalogue()


# ---------------------------------------------------------------------------
# Career-total computation
# ---------------------------------------------------------------------------


def _career_totals(db: Session, player_id: int) -> Dict[str, int]:
    """Sum (regular-season only) SeasonStat totals for a player.

    Returns ``{"pts": int, "fg3m": int, "ast": int, "reb": int}``. Missing
    columns are treated as 0.
    """
    rows = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
        .all()
    )
    totals = {"pts": 0, "fg3m": 0, "ast": 0, "reb": 0}
    for r in rows:
        totals["pts"] += int(r.pts or 0)
        totals["fg3m"] += int(r.fg3m or 0)
        totals["ast"] += int(r.ast or 0)
        totals["reb"] += int(r.reb or 0)
    return totals


def _current_season_pace(
    db: Session,
    player_id: int,
    season: Optional[str],
) -> Dict[str, float]:
    """Return per-game pace for (pts, fg3m, ast, reb) in the latest season.

    When ``season`` is provided, uses that season's regular-season SeasonStat
    row. When None, picks the player's most-recent regular-season row.
    Returns zeros when no row is found — the caller treats that as "no
    pace info, milestone is approaching but no ETA available".
    """
    query = (
        db.query(SeasonStat)
        .filter(
            SeasonStat.player_id == player_id,
            SeasonStat.is_playoff == False,  # noqa: E712
        )
    )
    if season:
        row = query.filter(SeasonStat.season == season).first()
    else:
        row = query.order_by(SeasonStat.season.desc()).first()

    if row is None:
        return {"pts": 0.0, "fg3m": 0.0, "ast": 0.0, "reb": 0.0}

    gp = int(row.gp or 0)
    if gp <= 0:
        return {"pts": 0.0, "fg3m": 0.0, "ast": 0.0, "reb": 0.0}

    return {
        "pts": float(row.pts_pg) if row.pts_pg is not None else (float(row.pts or 0) / gp),
        "fg3m": float(row.fg3m or 0) / gp,
        "ast": float(row.ast_pg) if row.ast_pg is not None else (float(row.ast or 0) / gp),
        "reb": float(row.reb_pg) if row.reb_pg is not None else (float(row.reb or 0) / gp),
    }


def _next_unhit_threshold(family: str, current_value: int) -> Optional[int]:
    """Return the next milestone threshold above ``current_value``, or None."""
    if family == "pts":
        thresholds = PTS_THRESHOLDS
    elif family == "fg3m":
        thresholds = THREE_PM_THRESHOLDS
    elif family == "ast":
        thresholds = AST_THRESHOLDS
    elif family == "reb":
        thresholds = REB_THRESHOLDS
    else:
        return None
    for t in thresholds:
        if current_value < t:
            return t
    return None


def _games_to_milestone(
    threshold: int, current_value: int, pace_per_game: float
) -> Optional[int]:
    """Estimate games remaining at the player's current per-game pace.

    Returns None when pace is non-positive (we can't extrapolate from a
    flat or negative trend) or when the milestone is already achieved.
    """
    if current_value >= threshold:
        return None
    if pace_per_game <= 0:
        return None
    remaining = threshold - current_value
    return int(math.ceil(remaining / pace_per_game))


def _achieved_in_game_id(
    db: Session,
    player_id: int,
    family: str,
    threshold: int,
    current_value: int,
) -> Tuple[Optional[str], Optional[_date]]:
    """Best-effort lookup of the game where ``threshold`` was crossed.

    Walks ``PlayerGameLog`` in reverse-chronological order, accumulating
    the running career total backwards until we cross the threshold.
    Returns ``(game_id, game_date)`` of the crossing game when found.
    Returns ``(None, None)`` when game logs don't span the milestone.
    """
    if current_value < threshold:
        return None, None

    column_map = {
        "pts": PlayerGameLog.pts,
        "fg3m": PlayerGameLog.fg3m,
        "ast": PlayerGameLog.ast,
        "reb": PlayerGameLog.reb,
    }
    col = column_map.get(family)
    if col is None:
        return None, None

    logs_desc = (
        db.query(PlayerGameLog)
        .filter(
            PlayerGameLog.player_id == player_id,
            PlayerGameLog.season_type == "Regular Season",
        )
        .order_by(
            PlayerGameLog.game_date.desc().nullslast(),
            PlayerGameLog.game_id.desc(),
        )
        .all()
    )

    running = current_value
    crossing: Optional[PlayerGameLog] = None
    for log in logs_desc:
        value = getattr(log, family) or 0
        before = running - int(value)
        if before < threshold <= running:
            crossing = log
            break
        running = before
        if running < threshold:
            crossing = log
            break

    if crossing is None:
        return None, None
    return crossing.game_id, crossing.game_date


# ---------------------------------------------------------------------------
# Snapshot UPSERT path
# ---------------------------------------------------------------------------


def _upsert_snapshot(
    db: Session,
    player_id: int,
    milestone_key: str,
    threshold: int,
    current_value: float,
    games_to_milestone: Optional[int],
    achieved_on: Optional[_date],
    achieved_in_game_id: Optional[str],
    season: Optional[str],
) -> MilestoneSnapshot:
    row = (
        db.query(MilestoneSnapshot)
        .filter(
            MilestoneSnapshot.player_id == player_id,
            MilestoneSnapshot.milestone_key == milestone_key,
        )
        .first()
    )
    if row is None:
        row = MilestoneSnapshot(
            player_id=player_id,
            milestone_key=milestone_key,
            threshold=threshold,
            current_value=current_value,
            games_to_milestone=games_to_milestone,
            achieved_on=achieved_on,
            achieved_in_game_id=achieved_in_game_id,
            season=season,
            is_career_milestone=True,
        )
        db.add(row)
    else:
        row.threshold = threshold
        row.current_value = current_value
        row.games_to_milestone = games_to_milestone
        row.achieved_on = achieved_on
        row.achieved_in_game_id = achieved_in_game_id
        row.season = season
        row.is_career_milestone = True
    return row


def compute_player_milestones(
    db: Session,
    player_id: int,
    season: Optional[str] = None,
) -> List[MilestoneSnapshot]:
    """Recompute and UPSERT all milestone rows for one player.

    For each (family, threshold) in the catalogue, writes a snapshot row.
    No commit — caller owns the txn.
    """
    totals = _career_totals(db, player_id)
    pace = _current_season_pace(db, player_id, season)

    written: List[MilestoneSnapshot] = []
    for key, family, threshold, _label in MILESTONE_CATALOGUE:
        current_value = int(totals.get(family, 0))
        if current_value >= threshold:
            game_id, game_date = _achieved_in_game_id(
                db, player_id, family, threshold, current_value
            )
            row = _upsert_snapshot(
                db,
                player_id=player_id,
                milestone_key=key,
                threshold=threshold,
                current_value=float(current_value),
                games_to_milestone=None,
                achieved_on=game_date,
                achieved_in_game_id=game_id,
                season=season,
            )
            written.append(row)
            continue

        games_to = _games_to_milestone(threshold, current_value, pace.get(family, 0.0))
        row = _upsert_snapshot(
            db,
            player_id=player_id,
            milestone_key=key,
            threshold=threshold,
            current_value=float(current_value),
            games_to_milestone=games_to,
            achieved_on=None,
            achieved_in_game_id=None,
            season=season,
        )
        written.append(row)
    return written


def compute_milestone_snapshots(
    db: Session,
    season: Optional[str] = None,
) -> Dict[str, int]:
    """Recompute milestone snapshots for every active player.

    "Active" here means ``Player.is_active=True`` — we don't recompute for
    retired players (their totals are static, no point burning queries).

    Returns ``{"players_processed": int, "snapshots_written": int}``.
    """
    players = db.query(Player).filter(Player.is_active == True).all()  # noqa: E712
    snapshots_written = 0
    for player in players:
        rows = compute_player_milestones(db, int(player.id), season=season)
        snapshots_written += len(rows)
    return {
        "players_processed": len(players),
        "snapshots_written": snapshots_written,
    }


def fetch_approaching_milestones(
    db: Session,
    limit: int = 20,
) -> List[Dict[str, object]]:
    """Return the closest approaching milestones across the league.

    Filters out achieved milestones (``games_to_milestone IS NULL``) and
    sorts by ``games_to_milestone`` ascending so the nearest pop first.
    Materializes player + team metadata so the API response is one query.
    """
    rows = (
        db.query(MilestoneSnapshot, Player, Team)
        .join(Player, Player.id == MilestoneSnapshot.player_id)
        .outerjoin(Team, Team.id == Player.team_id)
        .filter(MilestoneSnapshot.games_to_milestone.isnot(None))
        .order_by(MilestoneSnapshot.games_to_milestone.asc())
        .limit(limit)
        .all()
    )

    out: List[Dict[str, object]] = []
    for snap, player, team in rows:
        # Resolve label by reverse-lookup against the catalogue.
        label = next(
            (lbl for (k, _f, _t, lbl) in MILESTONE_CATALOGUE if k == snap.milestone_key),
            snap.milestone_key,
        )
        remaining = float(snap.threshold) - float(snap.current_value)
        out.append({
            "player_id": int(snap.player_id),
            "player_name": player.full_name if player and player.full_name else "Player {0}".format(snap.player_id),
            "team_abbreviation": (team.abbreviation if team else None) or None,
            "milestone_key": snap.milestone_key,
            "milestone_label": label,
            "threshold": int(snap.threshold),
            "current_value": float(snap.current_value),
            "games_to_milestone": int(snap.games_to_milestone) if snap.games_to_milestone is not None else None,
            "points_remaining": remaining if remaining > 0 else 0.0,
            "achieved_on": snap.achieved_on,
            "season": snap.season,
        })
    return out


__all__ = [
    "MILESTONE_CATALOGUE",
    "compute_milestone_snapshots",
    "compute_player_milestones",
    "fetch_approaching_milestones",
]
