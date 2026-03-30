#!/usr/bin/env python3
"""Season-scoped queue runner for warehouse ingestion jobs."""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import IngestionJob
from services.warehouse_service import get_job_summary, queue_backfill_season, run_next_job

def _handle_termination(_signum: int, _frame: object) -> None:
    raise SystemExit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_termination)
    signal.signal(signal.SIGINT, _handle_termination)
    parser = argparse.ArgumentParser(description="Run warehouse ingestion jobs for a season")
    parser.add_argument("--season", required=True, help="Season in YYYY-YY format, e.g. 2024-25")
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=25,
        help="Maximum number of queued jobs to dispatch in this run",
    )
    parser.add_argument(
        "--bootstrap-backfill",
        action="store_true",
        help="Queue a season backfill first when no pending jobs exist for this season",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep polling for work instead of exiting once the queue is empty",
    )
    parser.add_argument(
        "--idle-sleep",
        type=int,
        default=15,
        help="Seconds to sleep between idle polls in --loop mode",
    )
    parser.add_argument(
        "--summary-every",
        type=int,
        default=25,
        help="Print a queue summary every N dispatched jobs in --loop mode",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print the current queue summary for the season and exit",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.summary_only:
            print(get_job_summary(db, season=args.season))
            return

        pending = db.query(IngestionJob).filter_by(season=args.season, status="queued").count()
        if pending == 0 and args.bootstrap_backfill:
            jobs = queue_backfill_season(db, args.season)
            db.commit()
            print({"status": "queued_backfill", "season": args.season, "jobs": len(jobs)})

        dispatched = 0
        results = []
        while args.loop or dispatched < args.max_jobs:
            result = run_next_job(db, season=args.season)
            if result.get("status") == "idle":
                if not args.loop:
                    break
                print(
                    {
                        "status": "idle",
                        "season": args.season,
                        "jobs_dispatched": dispatched,
                        "summary": get_job_summary(db, season=args.season),
                    }
                )
                time.sleep(max(args.idle_sleep, 1))
                continue
            if args.loop:
                if dispatched == 0 or ((dispatched + 1) % max(args.summary_every, 1) == 0):
                    print(
                        {
                            "status": "progress",
                            "season": args.season,
                            "jobs_dispatched": dispatched + 1,
                            "last_result": result,
                            "summary": get_job_summary(db, season=args.season),
                        }
                    )
            else:
                results.append(result)
            dispatched += 1

        if not args.loop:
            print(
                {
                    "status": "ok",
                    "season": args.season,
                    "jobs_dispatched": dispatched,
                    "results": results,
                    "summary": get_job_summary(db, season=args.season),
                }
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
