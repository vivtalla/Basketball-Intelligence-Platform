#!/usr/bin/env python3
"""Ingest today's final-status playoff games into the DB.

The general sync (`bulk_import.py`, `pbp_import.py`) iterates games already in
GameLog. Today's just-finished games may not be in GameLog yet — they're only
on the live CDN scoreboard. This script:

1. Fetches today's scoreboard from the live CDN.
2. Filters to playoff games marked Final (gameStatus=3).
3. For any game_id not in GameLog, fetches its box score and inserts a
   GameLog row with season_type="Playoffs" and the game date.
4. Calls `build_or_refresh_bracket()` to recompute PlayoffSeries.top_wins /
   bottom_wins / status from the freshly-ingested games.
5. Optionally runs a focused PBP sync on the new games so the game-detail
   page is fully populated.

Usage:
    python data/sync_today_playoff_finals.py --season 2025-26
    python data/sync_today_playoff_finals.py --season 2025-26 --skip-pbp
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import GameLog, PlayByPlay
from data.nba_client import (
    get_game_box_score,
    get_play_by_play,
    get_todays_scoreboard,
)
from services.pbp_sync_service import (
    _ensure_box_score_entities,
    _store_pbp_events,
    _replace_pbp_events,
)
from services.playoff_bracket_service import build_or_refresh_bracket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("sync_today_finals")

PBP_REQUEST_DELAY = 0.6


def _scoreboard_finals():
    """Return list of (game_id, gameTimeUTC date) for Final playoff games today."""
    payload = get_todays_scoreboard()
    games = (payload.get("scoreboard") or {}).get("games") or []
    finals = []
    for g in games:
        gid = (g.get("gameId") or "").strip()
        if not gid.startswith("004"):
            continue
        if g.get("gameStatus") != 3:
            continue  # 1=upcoming, 2=live, 3=final
        finals.append(g)
    return finals


def _date_from_scoreboard(game: dict):
    raw = game.get("gameTimeUTC") or ""
    try:
        # gameTimeUTC is the tipoff in UTC; the actual calendar date in
        # NBA scheduling terms is whichever day the scoreboard is for.
        # Use gameCode (YYYYMMDD/AWAYHOME) for the calendar date.
        gc = game.get("gameCode") or ""
        ymd = gc.split("/")[0]  # "20260428"
        if len(ymd) == 8 and ymd.isdigit():
            return datetime.strptime(ymd, "%Y%m%d").date()
    except Exception:
        pass
    if raw:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def main():
    parser = argparse.ArgumentParser(description="Ingest today's playoff finals")
    parser.add_argument("--season", required=True, help="Season string, e.g. 2025-26")
    parser.add_argument("--skip-pbp", action="store_true", help="Skip PBP fetch for new games")
    args = parser.parse_args()

    finals = _scoreboard_finals()
    log.info("Scoreboard reports %d final playoff games today", len(finals))

    if not finals:
        log.info("Nothing to do.")
        return

    db = SessionLocal()
    new_game_ids = []
    try:
        for sb in finals:
            game_id = sb["gameId"]
            existing = db.query(GameLog).filter_by(game_id=game_id).first()
            if existing is not None and existing.home_score is not None:
                log.info("%s already in GameLog with scores — skipping ingest", game_id)
                continue

            # Fetch box score from NBA API to get authoritative team IDs +
            # final scores.
            time.sleep(PBP_REQUEST_DELAY)
            box = get_game_box_score(game_id)
            _ensure_box_score_entities(db, box)

            calendar_date = _date_from_scoreboard(sb)
            if existing is None:
                row = GameLog(
                    game_id=game_id,
                    season=args.season,
                    game_date=calendar_date,
                    home_team_id=box.get("home_team_id"),
                    away_team_id=box.get("away_team_id"),
                    home_score=box.get("home_score"),
                    away_score=box.get("away_score"),
                    season_type="Playoffs",
                )
                db.add(row)
                log.info(
                    "Inserted %s (%s @ %s, %s-%s, %s) into GameLog",
                    game_id,
                    box.get("away_team_abbreviation"),
                    box.get("home_team_abbreviation"),
                    box.get("away_score"),
                    box.get("home_score"),
                    calendar_date,
                )
            else:
                existing.season = args.season
                existing.game_date = calendar_date or existing.game_date
                existing.home_team_id = box.get("home_team_id")
                existing.away_team_id = box.get("away_team_id")
                existing.home_score = box.get("home_score")
                existing.away_score = box.get("away_score")
                existing.season_type = "Playoffs"
                log.info(
                    "Updated %s with final scores %s-%s",
                    game_id,
                    box.get("away_score"),
                    box.get("home_score"),
                )
            db.commit()
            new_game_ids.append(game_id)

        # Refresh PlayoffSeries aggregates so top_wins/bottom_wins reflect
        # the newly-ingested games.
        if new_game_ids:
            count = build_or_refresh_bracket(db, args.season)
            db.commit()
            log.info("Refreshed bracket: %d series rows touched", count)

        # PBP sync for the new games so the game-detail page is fully
        # populated. Skip if --skip-pbp.
        if not args.skip_pbp:
            for game_id in new_game_ids:
                already_have_pbp = db.query(PlayByPlay.id).filter_by(game_id=game_id).first()
                if already_have_pbp:
                    log.info("%s already has PBP — skipping fetch", game_id)
                    continue
                try:
                    time.sleep(PBP_REQUEST_DELAY)
                    pbp_events = get_play_by_play(game_id)
                    _store_pbp_events(db, game_id, pbp_events)
                    db.commit()
                    log.info("%s PBP synced — %d events", game_id, len(pbp_events))
                except Exception as exc:
                    db.rollback()
                    log.warning("PBP fetch failed for %s: %s", game_id, exc)
    finally:
        db.close()

    log.info("Done. Ingested %d games.", len(new_game_ids))


if __name__ == "__main__":
    main()
