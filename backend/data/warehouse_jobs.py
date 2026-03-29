#!/usr/bin/env python3
"""CLI entrypoint for warehouse ingestion jobs."""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from services.warehouse_service import (
    materialize_season_aggregates,
    queue_backfill_season,
    queue_current_season_daily_sync,
    run_next_job,
    sync_schedule,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run warehouse ingestion jobs")
    sub = parser.add_subparsers(dest="command", required=True)

    season_backfill = sub.add_parser("backfill-season")
    season_backfill.add_argument("--season", required=True)

    season_sync = sub.add_parser("sync-schedule")
    season_sync.add_argument("--season", required=True)
    season_sync.add_argument("--date")

    current_sync = sub.add_parser("queue-current-season")
    current_sync.add_argument("--season", required=True)

    mat = sub.add_parser("materialize-season")
    mat.add_argument("--season", required=True)

    sub.add_parser("run-next")

    args = parser.parse_args()
    db = SessionLocal()
    try:
        if args.command == "backfill-season":
            jobs = queue_backfill_season(db, args.season)
            db.commit()
            print({"queued": len(jobs), "season": args.season})
        elif args.command == "sync-schedule":
            print(sync_schedule(db, args.season, args.date))
        elif args.command == "queue-current-season":
            jobs = queue_current_season_daily_sync(db, args.season)
            db.commit()
            print({"queued": len(jobs), "season": args.season})
        elif args.command == "materialize-season":
            print(materialize_season_aggregates(db, args.season))
        elif args.command == "run-next":
            print(run_next_job(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
