"""Sprint 98 — Regular-season game-log gap detection + backfill.

Mirrors Sprint 97's ``playoff_series_backfill`` for regular-season games. The
playoff version walks ``PlayoffSeries`` rows and probes per-series-slot game
IDs; the regular season has no series structure, so this version compares
the NBA CDN schedule for a recent window to ``game_logs`` and inserts any
final-status games the cron missed.

Why the playoff backfill alone isn't sufficient: the same cron-failure /
NBA-API-flake / parser-bug class of issue that lost 4 R2 G1s during the
playoffs can lose any number of regular-season games during the regular
season. Without a gap detector on the larger surface, we'd only catch
drift via user reports.

Idempotent and rate-limited: 1 CDN schedule fetch + 0.6s between per-game
``boxscoresummaryv2`` probes. Returns the list of game_ids actually
backfilled; empty list = no gaps found.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from sqlalchemy.orm import Session

from db.models import GameLog

logger = logging.getLogger(__name__)

NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}
BOXSCORE_SUMMARY_URL = "https://stats.nba.com/stats/boxscoresummaryv2"
REGULAR_SEASON_PREFIX = "002"
REQUEST_TIMEOUT_SECONDS = 15
REQUEST_DELAY_SECONDS = 0.6  # match nba_client rate limit
DEFAULT_DAYS_BACK = 14


def _fetch_game_summary(game_id: str) -> Optional[Dict]:
    """Fetch NBA boxscoresummaryv2 for a candidate game_id.

    Returns ``{game_id, game_date, home_team_id, away_team_id, home_score,
    away_score}`` if NBA reports the game as Final. Returns ``None`` for
    non-final games, network failures, or malformed responses.
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
    except Exception as exc:  # noqa: BLE001 — network errors non-fatal
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
        "game_date": gs[0][:10],
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_score": scores.get(home_team_id),
        "away_score": scores.get(away_team_id),
    }


def _enumerate_schedule_finals(
    season: str,
    days_back: int,
    today: date,
    fetch_schedule_fn,
) -> List[Tuple[str, date]]:
    """Walk the season schedule and return ``[(game_id, game_date), ...]``
    for every regular-season game marked Final within the window.

    Window is ``[today - days_back, today - 1]`` — we exclude today
    because the post-game cron path owns same-day ingest.
    """
    try:
        payload_envelope = fetch_schedule_fn(season)
    except Exception as exc:  # noqa: BLE001
        logger.warning("schedule fetch failed for %s: %s", season, exc)
        return []

    payload = payload_envelope.get("payload") if payload_envelope else None
    if not payload:
        return []

    window_start = today - timedelta(days=days_back)
    window_end = today - timedelta(days=1)

    # The CDN schedule and the mobile schedule have different shapes.
    # Prefer the CDN form (leagueSchedule.gameDates[].games[]); fall back
    # to the mobile form (lscd[].mscd.g[]) if the keys aren't there.
    finals: List[Tuple[str, date]] = []
    league_schedule = payload.get("leagueSchedule")
    if league_schedule:
        for game_date in league_schedule.get("gameDates", []):
            for game in game_date.get("games", []):
                gid = str(game.get("gameId") or "").strip()
                if not gid.startswith(REGULAR_SEASON_PREFIX):
                    continue
                if int(game.get("gameStatus") or 0) != 3:
                    continue
                game_d = _parse_cdn_game_date(game)
                if game_d is None:
                    continue
                if window_start <= game_d <= window_end:
                    finals.append((gid, game_d))
    else:
        # Mobile schedule fallback.
        for month in payload.get("lscd", []):
            for game in month.get("mscd", {}).get("g", []):
                gid = str(game.get("gid") or "").strip()
                if not gid.startswith(REGULAR_SEASON_PREFIX):
                    continue
                # Mobile format uses `stt` for status text; only 'Final'
                # marks completed games.
                if (game.get("stt") or "").strip() != "Final":
                    continue
                game_d = _parse_mobile_game_date(game)
                if game_d is None:
                    continue
                if window_start <= game_d <= window_end:
                    finals.append((gid, game_d))

    return finals


def _parse_cdn_game_date(game: Dict) -> Optional[date]:
    """Pull a calendar date from a CDN-schedule game entry."""
    # gameCode = "YYYYMMDD/AWYHME"
    gc = game.get("gameCode") or ""
    ymd = gc.split("/")[0]
    if len(ymd) == 8 and ymd.isdigit():
        try:
            return datetime.strptime(ymd, "%Y%m%d").date()
        except ValueError:
            pass
    # gameDateEst is "YYYY-MM-DDT00:00:00Z"
    raw = game.get("gameDateEst") or game.get("gameDateUTC") or ""
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _parse_mobile_game_date(game: Dict) -> Optional[date]:
    """Pull a calendar date from a mobile-schedule game entry. `gdte` is the
    home-time game date string, e.g. ``"2024-12-25"``.
    """
    raw = (game.get("gdte") or game.get("gdtutc") or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def detect_and_backfill_regular_season_gaps(
    db: Session,
    season: str,
    *,
    days_back: int = DEFAULT_DAYS_BACK,
    today: Optional[date] = None,
    fetch_schedule_fn=None,
    fetch_summary_fn=_fetch_game_summary,
    sleep_fn=time.sleep,
) -> List[str]:
    """Detect and backfill missing regular-season games over a recent window.

    Algorithm:
        1. Fetch the season schedule once (1 CDN call).
        2. Filter to regular-season Finals with ``game_date`` in
           ``[today - days_back, today - 1]``.
        3. Compare against ``GameLog`` rows for that season + ``Regular Season``.
        4. For each missing game_id, fetch boxscoresummaryv2 and insert if
           NBA still reports Final. Probes are throttled to 0.6s.

    Args:
        db: SQLAlchemy session.
        season: e.g. ``"2025-26"``.
        days_back: how many days behind today to scan. Default 14.
        today: injected for testing; defaults to ``date.today()``.
        fetch_schedule_fn: returns the schedule payload envelope
            ``{"source": "...", "payload": {...}}``. Defaults to the
            lazy import of ``nba_client.get_schedule_payload_for_season``
            so tests can stub it without circular imports.
        fetch_summary_fn: per-game boxscoresummary fetcher (injectable).
        sleep_fn: injectable rate-limit pause between fetches.

    Returns:
        List of game_ids actually inserted. Empty list = no gaps found.
    """
    if today is None:
        today = date.today()
    if fetch_schedule_fn is None:
        from data.nba_client import get_schedule_payload_for_season

        fetch_schedule_fn = get_schedule_payload_for_season

    schedule_finals = _enumerate_schedule_finals(season, days_back, today, fetch_schedule_fn)
    if not schedule_finals:
        return []

    expected_ids = {gid for gid, _ in schedule_finals}
    existing_rows = (
        db.query(GameLog.game_id)
        .filter(
            GameLog.season == season,
            GameLog.season_type == "Regular Season",
            GameLog.game_id.in_(expected_ids),
        )
        .all()
    )
    existing_ids = {row[0] for row in existing_rows}
    missing = [(gid, gdate) for gid, gdate in schedule_finals if gid not in existing_ids]
    if not missing:
        return []

    backfilled: List[str] = []
    for index, (gid, _scheduled_date) in enumerate(missing):
        if index > 0 and sleep_fn:
            sleep_fn(REQUEST_DELAY_SECONDS)
        summary = fetch_summary_fn(gid)
        if summary is None:
            # NBA's per-game endpoint contradicts the schedule (or is
            # transiently failing) — skip but keep probing the rest.
            continue

        game_date_raw = summary["game_date"]
        game_date = (
            datetime.strptime(game_date_raw, "%Y-%m-%d").date()
            if isinstance(game_date_raw, str)
            else game_date_raw
        )

        db.add(
            GameLog(
                game_id=summary["game_id"],
                season=season,
                game_date=game_date,
                home_team_id=summary["home_team_id"],
                away_team_id=summary["away_team_id"],
                home_score=summary["home_score"],
                away_score=summary["away_score"],
                season_type="Regular Season",
            )
        )
        backfilled.append(gid)
        logger.warning(
            "BACKFILL: inserted missing regular-season game %s (%s)",
            gid, game_date,
        )

    if backfilled:
        db.commit()

    # Always write the freshness marker — including the zero-backfill case
    # — so the endpoint can distinguish "ran recently, found nothing" from
    # "never ran." Failures are non-fatal.
    try:
        from services.sync_freshness import record_sync

        record_sync(
            "regular_season_gap",
            count=len(backfilled),
            source="post_game_cron",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to write regular_season_gap marker: %s", exc)

    return backfilled


__all__ = ["detect_and_backfill_regular_season_gaps"]
