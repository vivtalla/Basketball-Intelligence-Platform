#!/usr/bin/env python3
"""Targeted PBP sync for playoff games.

Sprint 79 Stream B: the prior version of this script intentionally skipped the
derivation pipeline (PlayerOnOff / LineupStats / SeasonStat clutch_*) because
``_sync_games`` hardcoded ``is_playoff=False`` and would have corrupted
regular-season aggregates. With the ``is_playoff`` cascade fixed, we now run
the derivations with ``is_playoff=True`` after the per-game event fetch
completes. Regular-season rows are not touched.

Two phases per run:
    1. Fetch box score + PBP for every playoff game in GameLog, store the
       events in ``play_by_play``, ensure team/player entities exist.
    2. Run ``sync_pbp_for_playoffs_from_db`` to derive on/off + lineups +
       SeasonStat.clutch_* fields for those games. Non-fatal if it fails.

Usage:
    python data/sync_playoff_pbp.py --season 2025-26
    python data/sync_playoff_pbp.py --season 2025-26 --force-refresh
    python data/sync_playoff_pbp.py --season 2025-26 --skip-derivations
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
    sync_pbp_for_playoffs_from_db,
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
    parser.add_argument(
        "--skip-derivations",
        action="store_true",
        help="Only fetch+store events. Skip the on/off + lineup derivation phase.",
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
            "Event fetch done. fetched=%d reused=%d failed=%d total=%d",
            fetched, reused, failed, total,
        )

        if args.skip_derivations:
            log.info("--skip-derivations: not running on/off + lineup derivations")
        else:
            log.info("Running playoff PBP derivations (on/off + lineups + clutch)...")
            try:
                result = sync_pbp_for_playoffs_from_db(
                    db, args.season, force_refresh=args.force_refresh
                )
                log.info(
                    "Derivations done. games_processed=%d players_updated=%d",
                    result.get("games_processed", 0),
                    result.get("players_updated", 0),
                )
            except Exception as exc:
                log.warning("Playoff PBP derivations failed: %s", exc)
    finally:
        db.close()


if __name__ == "__main__":
    main()
