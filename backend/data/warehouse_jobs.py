#!/usr/bin/env python3
"""Season-scoped queue runner for warehouse ingestion jobs."""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import IngestionJob
from services.warehouse_service import queue_backfill_season, run_next_job


def main() -> None:
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
    args = parser.parse_args()

    db = SessionLocal()
    try:
        pending = db.query(IngestionJob).filter_by(season=args.season, status="queued").count()
        if pending == 0 and args.bootstrap_backfill:
            jobs = queue_backfill_season(db, args.season)
            db.commit()
            print({"status": "queued_backfill", "season": args.season, "jobs": len(jobs)})

        dispatched = 0
        results = []
        while dispatched < args.max_jobs:
            result = run_next_job(db, season=args.season)
            if result.get("status") == "idle":
                break
            results.append(result)
            dispatched += 1

        print(
            {
                "status": "ok",
                "season": args.season,
                "jobs_dispatched": dispatched,
                "results": results,
            }
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
