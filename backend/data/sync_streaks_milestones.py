#!/usr/bin/env python3
"""Sprint 78 CF5 — nightly streaks + milestones snapshot refresh.

Recomputes both ``player_streaks`` and ``milestone_snapshots`` for the
season passed via ``--season``. Idempotent — safe to re-run on every cron
tick.

Usage:
    python data/sync_streaks_milestones.py --season 2025-26
    python data/sync_streaks_milestones.py --season 2025-26 --dry-run

Wired into ``daily_sync.sh`` (post-game block + morning daily run) so the
``/milestones`` page always reads fresh snapshots after any new game.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Recompute streaks + milestone snapshots.")
    parser.add_argument("--season", required=True, help="Season string, e.g. 2025-26")
    parser.add_argument("--dry-run", action="store_true", help="Print intended actions, do nothing.")
    args = parser.parse_args()

    if args.dry_run:
        print(
            "sync_streaks_milestones dry-run: season={0}".format(args.season)
        )
        return 0

    # Defer imports past arg parsing so --help is fast.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("sync_streaks_milestones")

    from db.database import SessionLocal
    from services.milestone_proximity_service import compute_milestone_snapshots
    from services.streak_detection_service import compute_active_streaks

    db = SessionLocal()
    try:
        streak_summary = compute_active_streaks(db, season=args.season)
        log.info("streaks: %s", streak_summary)
        milestone_summary = compute_milestone_snapshots(db, season=args.season)
        log.info("milestones: %s", milestone_summary)
        db.commit()
    except Exception:  # pragma: no cover — log + re-raise so cron picks it up
        db.rollback()
        log.exception("sync_streaks_milestones failed")
        return 1
    finally:
        db.close()

    print(
        "sync_streaks_milestones complete: season={0}".format(args.season)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
