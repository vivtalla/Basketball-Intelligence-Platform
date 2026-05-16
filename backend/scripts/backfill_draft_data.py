"""Sprint 100 (Stream B) — one-shot historical draft-data backfill.

For each draft year in ``[start_year, end_year]`` (default 2016-2025):

  1. Run the Sports Reference CBB scraper for that season-end year.
  2. Run the NBA Combine scraper.
  3. Run the RealGM + G-League scrapers.

All ingest is idempotent (upsert keys are documented in each ingest_*
script), so re-running is safe.

This script lives in ``backend/scripts/`` (not ``data/``) and is NOT
called by cron — it's a manual one-time backfill. Run during off-peak
hours; each year takes ~2-5 minutes of network time. Holds the
``daily_sync.sh`` flock implicitly only through the SessionLocal —
explicit ``BIP_SYNC_LOCKFILE`` coordination is optional.

Usage::

    python -m scripts.backfill_draft_data --start-year 2016 --end-year 2025
    python -m scripts.backfill_draft_data --start-year 2025 --end-year 2026  # current + last
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ingest_combine import ingest_combine
from data.ingest_international import ingest_international
from data.ingest_mock_drafts import ingest_mock_drafts
from data.scrapers._base import ScraperError
from db.database import SessionLocal
from data.sync_draft_prospects import sync_sportsreference, DEFAULT_CSV_PATH

logger = logging.getLogger(__name__)


def _backfill_year(year: int) -> Dict[str, Any]:
    """Run every draft-data source for a single year."""
    summary: Dict[str, Any] = {"year": year}

    # 1. Sports Reference CBB — populates DraftProspect + per-season stats.
    db = SessionLocal()
    try:
        sr_counts = sync_sportsreference(
            db,
            draft_year=year,
            season="{0}-{1}".format(year - 1, str(year)[-2:]),
            top_n=100,
            fallback_csv_path=DEFAULT_CSV_PATH,
        )
        summary["sportsreference"] = sr_counts
    except Exception as exc:  # pragma: no cover - top-level guard
        logger.warning("backfill: SR year=%d failed: %s", year, exc)
        summary["sportsreference"] = {"error": str(exc)}
    finally:
        db.close()

    # 2. Mock drafts — only meaningful for the upcoming draft (won't be
    # public for past years). Wrap in try; treat 0-prospect results
    # gracefully.
    try:
        summary["mock_drafts"] = ingest_mock_drafts(year)
    except Exception as exc:
        logger.warning("backfill: mock_drafts year=%d failed: %s", year, exc)
        summary["mock_drafts"] = {"error": str(exc)}

    # 3. Combine — historical years are still available.
    try:
        summary["combine"] = ingest_combine(year)
    except ScraperError as exc:
        logger.warning("backfill: combine year=%d failed: %s", year, exc)
        summary["combine"] = {"error": str(exc)}
    except Exception as exc:
        logger.warning("backfill: combine year=%d unexpected: %s", year, exc)
        summary["combine"] = {"error": str(exc)}

    # 4. International + G-League.
    try:
        summary["international"] = ingest_international(year)
    except Exception as exc:
        logger.warning("backfill: international year=%d failed: %s", year, exc)
        summary["international"] = {"error": str(exc)}

    return summary


def backfill(start_year: int, end_year: int) -> List[Dict[str, Any]]:
    summaries: List[Dict[str, Any]] = []
    for year in range(start_year, end_year + 1):
        logger.info("backfill_draft_data: starting year=%d", year)
        summaries.append(_backfill_year(year))
        logger.info("backfill_draft_data: year=%d summary=%s", year, summaries[-1])
    return summaries


def main(argv: list = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2016)
    parser.add_argument("--end-year", type=int, default=2026)
    args = parser.parse_args(argv)
    summaries = backfill(args.start_year, args.end_year)
    logger.info("backfill_draft_data: %d years processed", len(summaries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
