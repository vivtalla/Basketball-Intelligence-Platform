"""Sprint 100 (Stream B) — NBA Draft Combine ingest.

Pulls combine measurements for ``draft_year`` and upserts them into
``DraftProspectMeasurement`` on ``(prospect_id, combine_year)``. Prospects
without a matching ``DraftProspect`` row (by normalized full name + draft
year) are skipped — the canonical source of new prospect rows is the
Sports Reference scrape in ``sync_draft_prospects``.

Usage::

    python -m data.ingest_combine --year 2026
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from data.scrapers._base import ScraperError
from data.scrapers.nba_combine import NBACombineScraper, _normalize_name
from db.database import SessionLocal
from db.models import DraftProspect, DraftProspectMeasurement
from services.sync_freshness import record_sync

logger = logging.getLogger(__name__)


def _find_prospect(db: Session, draft_year: int, full_name: str) -> Optional[DraftProspect]:
    target = _normalize_name(full_name)
    if not target:
        return None
    for p in db.query(DraftProspect).filter(DraftProspect.draft_year == draft_year).all():
        if _normalize_name(p.full_name) == target:
            return p
    return None


def _upsert_measurement(
    db: Session,
    prospect: DraftProspect,
    measurement: Dict[str, Any],
) -> bool:
    """Upsert one measurement row.

    Combine rows are unique per (prospect_id, combine_year); if a row
    already exists for that year we update it in place.

    Returns True if a row was inserted (vs updated).
    """
    existing = (
        db.query(DraftProspectMeasurement)
        .filter(
            DraftProspectMeasurement.prospect_id == prospect.id,
            DraftProspectMeasurement.combine_year == measurement.get("combine_year"),
        )
        .order_by(DraftProspectMeasurement.id.desc())
        .first()
    )
    target = existing or DraftProspectMeasurement(prospect_id=prospect.id)
    for field in (
        "height_no_shoes", "height_with_shoes", "weight", "wingspan", "standing_reach",
        "body_fat_pct", "hand_length", "hand_width", "standing_vert", "max_vert",
        "lane_agility_seconds", "three_quarter_sprint_seconds", "bench_press_135",
        "combine_year", "source", "source_url",
    ):
        value = measurement.get(field)
        if value is not None:
            setattr(target, field, value)
    target.as_of = datetime.now(timezone.utc)
    if existing is None:
        db.add(target)
        return True
    return False


def ingest_combine(draft_year: int) -> Dict[str, Any]:
    scraper = NBACombineScraper()
    db = SessionLocal()
    inserted = 0
    updated = 0
    skipped = 0
    try:
        measurements = scraper.fetch_combine(draft_year)
        logger.info("ingest_combine: fetched %d measurements for %d", len(measurements), draft_year)
        for m in measurements:
            prospect = _find_prospect(db, draft_year, m["full_name"])
            if prospect is None:
                skipped += 1
                continue
            was_insert = _upsert_measurement(db, prospect, m)
            if was_insert:
                inserted += 1
            else:
                updated += 1
        db.commit()
        try:
            record_sync(
                "draft_combine",
                count=inserted + updated,
                source="ingest_combine",
            )
        except Exception:  # pragma: no cover - non-fatal
            logger.exception("record_sync(draft_combine) failed")
        return {
            "draft_year": draft_year,
            "inserted": inserted,
            "updated": updated,
            "skipped_no_prospect_match": skipped,
        }
    except ScraperError as exc:
        logger.warning("ingest_combine: scraper failure: %s", exc)
        try:
            record_sync("draft_combine", count=0, source="ingest_combine", error=str(exc))
        except Exception:  # pragma: no cover
            pass
        raise
    finally:
        db.close()


def main(argv: list = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args(argv)
    result = ingest_combine(args.year)
    logger.info("ingest_combine complete: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
