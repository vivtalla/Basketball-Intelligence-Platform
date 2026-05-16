"""Sprint 100 (Stream B) — mock-draft consensus ingest.

Orchestrates the three mock-draft scrapers (ESPN / NBADraft.net / CBS),
upserts per-source rows into ``draft_mock_rankings``, then recomputes
``DraftProspect.consensus_rank_float`` + ``consensus_variance`` for the
active draft year.

Failures on one source are non-fatal: we log + record via
``record_sync()`` and recompute consensus from whatever succeeded.

Usage::

    python -m data.ingest_mock_drafts --year 2026
    python -m data.ingest_mock_drafts --year 2026 --sources espn,cbs

The script is idempotent — the ``(prospect_id, source, as_of)`` unique
constraint means re-running on the same as_of timestamp is a no-op.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

# Path so ``python -m data.ingest_mock_drafts`` works from backend/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from data.scrapers._base import ScraperError
from data.scrapers.mock_drafts import (
    ESPNMockDraftScraper,
    NBADraftNetScraper,
    CBSMockDraftScraper,
    compute_consensus,
)
from data.scrapers.mock_drafts._consensus import normalize_name
from db.database import SessionLocal
from db.models import DraftMockRanking, DraftProspect
from services.sync_freshness import record_sync

logger = logging.getLogger(__name__)


SCRAPERS = {
    "espn": ESPNMockDraftScraper,
    "nbadraft_net": NBADraftNetScraper,
    "cbs": CBSMockDraftScraper,
}


def _fetch_all_sources(draft_year: int, sources: Iterable[str]) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    for source in sources:
        cls = SCRAPERS.get(source)
        if cls is None:
            logger.warning("ingest_mock_drafts: unknown source %s; skipping", source)
            continue
        scraper = cls()
        try:
            payload = scraper.fetch_board(draft_year)
            payloads.append(payload)
            logger.info("ingest_mock_drafts: %s returned %d rankings", source, len(payload["rankings"]))
        except ScraperError as exc:
            logger.warning("ingest_mock_drafts: %s failed: %s", source, exc)
            # No payload; consensus will degrade gracefully.
    return payloads


def _upsert_rankings(
    db: Session,
    draft_year: int,
    payloads: List[Dict[str, Any]],
) -> int:
    """Insert per-source rankings into ``draft_mock_rankings``.

    Idempotent: the ``(prospect_id, source, as_of)`` unique constraint
    means a re-run with the same as_of has nothing to do.

    Resolves prospect rows by ``DraftProspect.draft_year`` plus
    normalized full_name. Prospects not yet in ``DraftProspect`` are
    skipped — Sports Reference ingestion (already wired in
    ``sync_draft_prospects``) is the canonical source of new prospect
    rows.
    """
    # Build name→prospect lookup for this draft year.
    prospects = db.query(DraftProspect).filter(DraftProspect.draft_year == draft_year).all()
    name_to_prospect = {normalize_name(p.full_name): p for p in prospects}

    inserted = 0
    for payload in payloads:
        as_of = datetime.fromisoformat(payload["as_of"].replace("Z", "+00:00")) \
            if isinstance(payload.get("as_of"), str) else datetime.now(timezone.utc)
        for entry in payload.get("rankings", []):
            key = normalize_name(entry.get("name", ""))
            prospect = name_to_prospect.get(key)
            if prospect is None:
                logger.debug(
                    "ingest_mock_drafts: no DraftProspect match for %r in %s — skip",
                    entry.get("name"), payload["source"],
                )
                continue
            existing = (
                db.query(DraftMockRanking)
                .filter(
                    DraftMockRanking.prospect_id == prospect.id,
                    DraftMockRanking.source == payload["source"],
                    DraftMockRanking.as_of == as_of,
                )
                .one_or_none()
            )
            if existing is not None:
                # Same as_of → no-op. The constraint would block anyway.
                continue
            row = DraftMockRanking(
                prospect_id=prospect.id,
                source=payload["source"],
                source_url=payload.get("source_url"),
                as_of=as_of,
                rank=int(entry["rank"]),
                tier=entry.get("tier"),
                position_projected=entry.get("position"),
                comp_player_name=entry.get("comp"),
                notes=None,
            )
            db.add(row)
            inserted += 1
    db.flush()
    return inserted


def _recompute_consensus(db: Session, draft_year: int, payloads: List[Dict[str, Any]]) -> int:
    """Update ``DraftProspect.consensus_rank_float`` + ``consensus_variance``."""
    aggregates = compute_consensus(payloads)
    updated = 0
    for prospect in db.query(DraftProspect).filter(DraftProspect.draft_year == draft_year).all():
        agg = aggregates.get(normalize_name(prospect.full_name))
        if agg is None:
            # No mock-draft data for this prospect — leave fields untouched,
            # but null them out so the board doesn't keep stale aggregates.
            prospect.consensus_rank_float = None
            prospect.consensus_variance = None
            continue
        prospect.consensus_rank_float = agg["mean_rank"]
        prospect.consensus_variance = agg["stddev_rank"]
        updated += 1
    db.flush()
    return updated


def ingest_mock_drafts(
    draft_year: int,
    sources: Iterable[str] = ("espn", "nbadraft_net", "cbs"),
) -> Dict[str, Any]:
    """Public API used by ``sync_draft_prospects --source mock_drafts``."""
    sources = list(sources)
    payloads = _fetch_all_sources(draft_year, sources)
    db = SessionLocal()
    try:
        inserted = _upsert_rankings(db, draft_year, payloads)
        updated = _recompute_consensus(db, draft_year, payloads)
        db.commit()
        result = {
            "draft_year": draft_year,
            "sources_attempted": sources,
            "sources_returned": [p["source"] for p in payloads],
            "rankings_inserted": inserted,
            "prospects_consensus_updated": updated,
        }
        try:
            record_sync("draft_mock_rankings", count=inserted, source="ingest_mock_drafts")
        except Exception:  # pragma: no cover - non-fatal
            logger.exception("record_sync(draft_mock_rankings) failed")
        return result
    finally:
        db.close()


def main(argv: list = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026, help="Draft year (e.g. 2026)")
    parser.add_argument(
        "--sources",
        type=str,
        default="espn,nbadraft_net,cbs",
        help="Comma-separated source list",
    )
    args = parser.parse_args(argv)
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    result = ingest_mock_drafts(args.year, sources)
    logger.info("ingest_mock_drafts complete: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
