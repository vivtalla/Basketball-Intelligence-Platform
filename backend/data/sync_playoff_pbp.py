#!/usr/bin/env python3
"""Targeted PBP sync for playoff games.

The general-purpose `pbp_import.py` runs the full `_sync_games` flow which
also writes regular-season aggregate tables (clutch / on-off / lineup) with
`is_playoff=False`. Running it against playoff game IDs would corrupt those
regular-season aggregates with playoff numbers.

This script does just the per-game work — fetch box score + PBP, store the
events in `play_by_play`, ensure team/player entities exist — without any
aggregate computation. Safe to run against playoff games.

Usage:
    python data/sync_playoff_pbp.py --season 2025-26
    python data/sync_playoff_pbp.py --season 2025-26 --force-refresh
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import GameLog, PlayByPlay
from data.nba_client import get_game_box_score, get_play_by_play
from services.pbp_sync_service import (
    _ensure_box_score_entities,
    _get_or_create_game_log,
    _store_pbp_events,
    _replace_pbp_events,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("sync_playoff_pbp")

PBP_REQUEST_DELAY = 0.6  # seconds, matches services.pbp_sync_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync PBP for playoff games only")
    parser.add_argument("--season", required=True, help="Season string, e.g. 2025-26")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Re-fetch and replace PBP even if events already exist",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        playoff_games = (
            db.query(GameLog)
            .filter(
                GameLog.season == args.season,
                GameLog.season_type == "Playoffs",
            )
            .order_by(GameLog.game_date.asc(), GameLog.game_id.asc())
            .all()
        )

        if not playoff_games:
            log.warning("No playoff GameLog rows found for season=%s", args.season)
            return

        total = len(playoff_games)
        log.info("Found %d playoff games for %s", total, args.season)

        fetched = 0
        reused = 0
        failed = 0

        for idx, game in enumerate(playoff_games, start=1):
            game_id = game.game_id
            existing = (
                db.query(PlayByPlay.id).filter_by(game_id=game_id).first()
            )
            if existing and not args.force_refresh:
                log.info("[%d/%d] %s already has PBP — skipping", idx, total, game_id)
                reused += 1
                continue

            try:
                time.sleep(PBP_REQUEST_DELAY)
                box_score = get_game_box_score(game_id)
                _ensure_box_score_entities(db, box_score)
                _get_or_create_game_log(db, game_id, args.season, box_score)
                # Re-mark as playoff after refresh (the helper resets season_type
                # implicitly via box_score, but it doesn't write season_type).
                game.season_type = "Playoffs"

                time.sleep(PBP_REQUEST_DELAY)
                pbp_events = get_play_by_play(game_id)

                if existing and args.force_refresh:
                    _replace_pbp_events(db, game_id, pbp_events)
                else:
                    _store_pbp_events(db, game_id, pbp_events)
                db.commit()

                fetched += 1
                log.info(
                    "[%d/%d] %s synced — %d events",
                    idx, total, game_id, len(pbp_events),
                )
            except Exception as exc:
                db.rollback()
                failed += 1
                log.warning(
                    "[%d/%d] %s failed: %s", idx, total, game_id, exc
                )

        log.info(
            "Done. fetched=%d reused=%d failed=%d total=%d",
            fetched, reused, failed, total,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
