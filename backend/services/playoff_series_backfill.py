"""Sprint 97 — Playoff series gap detection + backfill.

Defends against the round-transition ingest gap surfaced on 2026-05-10
production review: all four R2 Game 1s were missing from `game_logs` even
though NBA's CDN had every one. The cause is a timing collision between
the post-game cron, the bracket builder, and NBA's `scoreboardv2` date
filtering. The post-game path only fetches "today's" finals, so a game
that finishes during a cron-window gap or before the parent PlayoffSeries
row is created can disappear entirely.

This service walks every active/closed PlayoffSeries and:
  1. Computes expected game IDs from existing rows' series-slot prefix.
  2. For any missing position from 1 up to (max_seen + 1), fetches NBA's
     `boxscoresummaryv2?GameID=...` — if NBA reports Final, inserts a
     `GameLog` row with `series_id` set and `series_game_num` derived
     from the position.
  3. Renumbers `series_game_num` for the affected series so date order
     stays consistent.

NBA game IDs in a playoff series follow `0042500SSG`: 4-digit playoff
prefix + 2-digit season year + 2-digit series-slot (10-23 for R1+R2 etc.)
+ 1-digit game number (1-7). So given any existing game's ID, we can
synthesize candidates for the same slot. Slot 21 = E-R2-BOT (PHI/NYK).

Idempotent — safe to call on every post-game cron tick. Returns the list
of game_ids actually backfilled; an empty list means no gaps were found.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from sqlalchemy.orm import Session

from db.models import GameLog, PlayoffSeries

logger = logging.getLogger(__name__)

NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}
BOXSCORE_SUMMARY_URL = "https://stats.nba.com/stats/boxscoresummaryv2"
MAX_GAMES_PER_SERIES = 7
REQUEST_TIMEOUT_SECONDS = 15
REQUEST_DELAY_SECONDS = 0.6  # match nba_client rate limit


def _parse_series_slot(game_id: Optional[str]) -> Optional[Tuple[str, int]]:
    """Parse a playoff game_id into (slot_prefix, game_num).

    ``0042500211`` → (``"004250021"``, ``1``).

    Returns None for non-playoff IDs or malformed inputs.
    """
    if not game_id or len(game_id) != 10 or not game_id.startswith("004"):
        return None
    try:
        game_num = int(game_id[9])
    except ValueError:
        return None
    return game_id[:9], game_num


def _fetch_game_summary(game_id: str) -> Optional[Dict]:
    """Fetch NBA boxscoresummaryv2 for a candidate game_id.

    Returns a dict with ``game_id``, ``game_date``, ``home_team_id``,
    ``away_team_id``, ``home_score``, ``away_score`` if NBA reports the
    game as Final. Returns None otherwise (game not found, not final,
    or network failure).
    """
    try:
        response = requests.get(
            BOXSCORE_SUMMARY_URL,
            params={"GameID": game_id},
            headers=NBA_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            return None
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 — network errors are non-fatal
        logger.warning("boxscoresummary fetch failed for %s: %s", game_id, exc)
        return None

    result_sets = {rs.get("name"): rs for rs in payload.get("resultSets", [])}
    game_summary = result_sets.get("GameSummary", {})
    line_score = result_sets.get("LineScore", {})

    gs_rows = game_summary.get("rowSet") or []
    ls_rows = line_score.get("rowSet") or []
    ls_headers = line_score.get("headers") or []
    if not gs_rows or not ls_rows or not ls_headers:
        return None

    gs = gs_rows[0]
    # GameSummary columns:
    # 0=GAME_DATE_EST 1=GAME_SEQUENCE 2=GAME_ID 3=GAME_STATUS_ID
    # 4=GAME_STATUS_TEXT 5=GAMECODE 6=HOME_TEAM_ID 7=VISITOR_TEAM_ID
    if gs[4] != "Final":
        return None

    try:
        tid_idx = ls_headers.index("TEAM_ID")
        pts_idx = ls_headers.index("PTS")
    except ValueError:
        return None
    scores = {row[tid_idx]: row[pts_idx] for row in ls_rows}

    home_team_id = gs[6]
    away_team_id = gs[7]
    return {
        "game_id": gs[2],
        "game_date": gs[0][:10],  # YYYY-MM-DD slice
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_score": scores.get(home_team_id),
        "away_score": scores.get(away_team_id),
    }


def _renumber_series_game_nums(db: Session, series_id: str) -> None:
    """Renumber series_game_num on every GameLog row for a series so the
    date order matches the position. Called after a backfill insert.
    """
    # Flush pending inserts so the renumber query sees rows we just added
    # this transaction. Sessions configured with autoflush=False (tests)
    # would otherwise miss the newly-inserted G1.
    db.flush()
    rows = (
        db.query(GameLog)
        .filter(GameLog.series_id == series_id)
        .order_by(GameLog.game_date, GameLog.game_id)
        .all()
    )
    for position, row in enumerate(rows, start=1):
        if row.series_game_num != position:
            row.series_game_num = position


def backfill_playoff_series_gaps(
    db: Session,
    season: str,
    *,
    max_game_num: int = MAX_GAMES_PER_SERIES,
    fetch_fn=_fetch_game_summary,
    sleep_fn=time.sleep,
) -> List[str]:
    """Detect and backfill missing playoff games for every active/closed series.

    For each ``PlayoffSeries`` row with status ``active`` or ``closed``:
        1. Determine the series-slot prefix from any existing GameLog row.
        2. Walk positions 1..(max_seen + 1). For each missing position,
           ask NBA. If NBA reports Final, insert a GameLog row.
        3. Renumber ``series_game_num`` after any insert.

    Args:
        db: SQLAlchemy session.
        season: e.g. ``"2025-26"``.
        max_game_num: ceiling for how many positions to probe per series.
            Defaults to 7 (the NBA playoff format max).
        fetch_fn: injectable for testing — defaults to live NBA fetch.
        sleep_fn: injectable rate-limit pause between fetches.

    Returns:
        List of game_ids actually inserted. Empty list = no gaps found.
    """
    series_rows = (
        db.query(PlayoffSeries)
        .filter(
            PlayoffSeries.season == season,
            PlayoffSeries.status.in_(["active", "closed"]),
        )
        .all()
    )

    backfilled: List[str] = []
    fetch_count = 0

    for series in series_rows:
        games = (
            db.query(GameLog)
            .filter(GameLog.series_id == series.series_id)
            .order_by(GameLog.game_id)
            .all()
        )
        if not games:
            # Series row exists but no games yet — wait for first ingest.
            continue

        slot_prefix: Optional[str] = None
        existing_nums: set = set()
        for g in games:
            parsed = _parse_series_slot(g.game_id)
            if parsed is None:
                continue
            slot, num = parsed
            if slot_prefix is None:
                slot_prefix = slot
            elif slot != slot_prefix:
                logger.warning(
                    "series %s has games from multiple slot prefixes (%s vs %s); skipping backfill",
                    series.series_id, slot_prefix, slot,
                )
                slot_prefix = None
                break
            existing_nums.add(num)

        if slot_prefix is None or not existing_nums:
            continue

        # Walk 1..max_seen+1 — checking one beyond seen catches a freshly
        # finished game whose post-game tick missed.
        ceiling = min(max(existing_nums) + 1, max_game_num)

        for position in range(1, ceiling + 1):
            if position in existing_nums:
                continue
            candidate_id = f"{slot_prefix}{position}"
            if fetch_count > 0 and sleep_fn:
                sleep_fn(REQUEST_DELAY_SECONDS)
            fetch_count += 1
            summary = fetch_fn(candidate_id)
            if summary is None:
                # NBA doesn't have this game (yet) — stop probing further
                # positions in this series; sequential numbering means
                # nothing beyond this should exist either.
                break

            # NBA returns dates as YYYY-MM-DD strings; SQLite (used in
            # tests) requires Python date objects, Postgres accepts both.
            game_date_raw = summary["game_date"]
            game_date = (
                datetime.strptime(game_date_raw, "%Y-%m-%d").date()
                if isinstance(game_date_raw, str)
                else game_date_raw
            )

            db.add(
                GameLog(
                    game_id=summary["game_id"],
                    season=series.season,
                    game_date=game_date,
                    home_team_id=summary["home_team_id"],
                    away_team_id=summary["away_team_id"],
                    home_score=summary["home_score"],
                    away_score=summary["away_score"],
                    season_type="Playoffs",
                    series_id=series.series_id,
                    series_game_num=position,
                )
            )
            existing_nums.add(position)
            backfilled.append(candidate_id)
            logger.warning(
                "BACKFILL: inserted missing playoff game %s (series %s, game %d)",
                candidate_id, series.series_id, position,
            )

        if backfilled:
            # Always renumber after any insert so the date order is canonical.
            _renumber_series_game_nums(db, series.series_id)

    if backfilled:
        db.commit()
        # Surface the event to /api/health/sync-status for monitoring.
        # 24h TTL means a single backfill stays visible across a full
        # day of observation. Failures here are non-fatal.
        try:
            from data.cache import CacheManager

            CacheManager.set(
                "sync_gaps:playoff_backfill:last",
                {
                    "ran_at": datetime.utcnow().isoformat() + "Z",
                    "season": season,
                    "count": len(backfilled),
                    "backfilled_ids": backfilled,
                },
                ttl_seconds=86400,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("failed to write sync-gap marker: %s", exc)

    return backfilled


__all__ = ["backfill_playoff_series_gaps"]
