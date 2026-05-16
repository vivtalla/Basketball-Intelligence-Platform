"""Sprint 100 (Stream B) — international + G League stats ingest.

Pulls per-season averages from RealGM (Euroleague/EuroCup/Adriatic/LNB)
and the NBA Stats G League endpoint, upserts into
``DraftInternationalStat`` keyed by ``(prospect_id, season, league)``.

Matching strategy: by normalized full-name within the current draft year.
We don't try to cross-link historical seasons here — that's the backfill
script's job.

Usage::

    python -m data.ingest_international --year 2026
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
from data.scrapers.nba_gleague import NBAGLeagueScraper
from data.scrapers.realgm_international import RealGMInternationalScraper
from data.scrapers.mock_drafts._consensus import normalize_name
from db.database import SessionLocal
from db.models import DraftInternationalStat, DraftProspect
from services.sync_freshness import record_sync

logger = logging.getLogger(__name__)


def _season_label(end_year: int) -> str:
    return "{0}-{1}".format(end_year - 1, str(end_year)[-2:])


def _find_prospect(db: Session, draft_year: int, full_name: str) -> Optional[DraftProspect]:
    target = normalize_name(full_name)
    if not target:
        return None
    for p in db.query(DraftProspect).filter(DraftProspect.draft_year == draft_year).all():
        if normalize_name(p.full_name) == target:
            return p
    return None


def _upsert_stat(
    db: Session,
    prospect: DraftProspect,
    season: str,
    league: str,
    row: Dict[str, Any],
    source: str,
    source_url: Optional[str],
) -> bool:
    """Upsert ``DraftInternationalStat`` on (prospect_id, season, league).

    Returns True if a row was inserted (vs updated).
    """
    existing = (
        db.query(DraftInternationalStat)
        .filter(
            DraftInternationalStat.prospect_id == prospect.id,
            DraftInternationalStat.season == season,
            DraftInternationalStat.league == league,
        )
        .one_or_none()
    )
    target = existing or DraftInternationalStat(
        prospect_id=prospect.id, season=season, league=league
    )
    for field in (
        "team_name", "games", "minutes_per_game", "ppg", "rpg", "apg", "spg",
        "bpg", "fg_pct", "three_pct", "ft_pct", "usage_rate", "ts_pct",
    ):
        value = row.get(field)
        if value is not None:
            setattr(target, field, value)
    target.source = source
    target.source_url = source_url
    target.as_of = datetime.now(timezone.utc)
    if existing is None:
        db.add(target)
        return True
    return False


def ingest_international(draft_year: int) -> Dict[str, Any]:
    db = SessionLocal()
    summary = {
        "draft_year": draft_year,
        "realgm_inserted": 0, "realgm_updated": 0, "realgm_skipped": 0, "realgm_error": None,
        "gleague_inserted": 0, "gleague_updated": 0, "gleague_skipped": 0, "gleague_error": None,
    }
    season = _season_label(draft_year)
    try:
        # RealGM — multi-league pull.
        try:
            realgm = RealGMInternationalScraper().fetch_all_leagues(season_end_year=draft_year)
        except ScraperError as exc:
            logger.warning("ingest_international: RealGM failed: %s", exc)
            summary["realgm_error"] = str(exc)
            realgm = []
        for row in realgm:
            prospect = _find_prospect(db, draft_year, row["player"])
            if prospect is None:
                summary["realgm_skipped"] += 1
                continue
            league_label = {
                1: "Euroleague", 2: "EuroCup", 18: "Adriatic", 4: "French LNB",
            }.get(row.get("league_id"), row.get("league_slug") or "International")
            inserted = _upsert_stat(
                db, prospect, season, league_label, row,
                source="realgm",
                source_url=row.get("source_url"),
            )
            if inserted:
                summary["realgm_inserted"] += 1
            else:
                summary["realgm_updated"] += 1

        # G League
        try:
            gleague = NBAGLeagueScraper().fetch_season(season_end_year=draft_year)
        except ScraperError as exc:
            logger.warning("ingest_international: G League failed: %s", exc)
            summary["gleague_error"] = str(exc)
            gleague = []
        for row in gleague:
            prospect = _find_prospect(db, draft_year, row["player"])
            if prospect is None:
                summary["gleague_skipped"] += 1
                continue
            inserted = _upsert_stat(
                db, prospect, season, "G League", row,
                source="nba_gleague",
                source_url=row.get("source_url"),
            )
            if inserted:
                summary["gleague_inserted"] += 1
            else:
                summary["gleague_updated"] += 1

        db.commit()
        try:
            total = (
                summary["realgm_inserted"] + summary["realgm_updated"]
                + summary["gleague_inserted"] + summary["gleague_updated"]
            )
            record_sync(
                "draft_international",
                count=total,
                source="ingest_international",
                error=summary["realgm_error"] or summary["gleague_error"],
            )
        except Exception:  # pragma: no cover - non-fatal
            logger.exception("record_sync(draft_international) failed")
        return summary
    finally:
        db.close()


def main(argv: list = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026)
    args = parser.parse_args(argv)
    result = ingest_international(args.year)
    logger.info("ingest_international complete: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
