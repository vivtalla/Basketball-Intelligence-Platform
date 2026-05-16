"""Sprint 100 (Stream A continuation) — historical draft-outcome backfill.

One-shot CLI for seeding 2016-2025 draft prospects + their NBA career
outcome rows. Run once during off-peak hours; subsequent re-runs are
idempotent (upsert on ``(draft_year, normalized_name)``).

Data source: a curated seed CSV at
``backend/data/seed/draft_outcomes_2016_2025.csv`` (committed to the
repo). The CSV needs columns:

    draft_year, draft_pick, full_name, school, primary_position,
    nba_player_name, career_games, career_minutes, career_ppg,
    career_ws, all_star_selections, all_nba_selections, as_of_season

Rationale: scraping Basketball-Reference's draft index for ten years of
historical data is doable but flaky (Cloudflare interception, table
layout changes by year). A curated CSV is faster to bootstrap, plays
nicely with CI, and is trivially correctable. The scrape path can be
added later as ``--source bbref`` once we have a steady cron.

Usage::

    python -m scripts.backfill_draft_outcomes --start-year 2016 --end-year 2025 --dry-run
    python -m scripts.backfill_draft_outcomes --start-year 2016 --end-year 2025

Resolves each historical prospect to an NBA ``players.id`` via
``draft_linkage_service.resolve_player_id``; unmatched prospects are
still written to ``draft_prospects`` (``is_historical=True``) but their
``draft_outcomes.player_id`` stays null and they're logged to
``unmatched_prospects_report.csv`` for manual fixup.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from db.database import SessionLocal
from db.models import (
    DraftOutcome, DraftProspect, DraftProspectLinkage, Player,
)
from services.draft_linkage_service import normalize_name, resolve_player_id
from services.draft_outcome_classifier import classify_outcome

logger = logging.getLogger(__name__)

DEFAULT_CSV_PATH = "data/seed/draft_outcomes_2016_2025.csv"


def _to_int(raw: Any) -> Optional[int]:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _to_float(raw: Any) -> Optional[float]:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _read_seed(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        logger.warning(
            "backfill_draft_outcomes: seed CSV not found at %s — nothing to do. "
            "Populate the CSV or use --source bbref (not yet implemented).",
            path,
        )
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _upsert_prospect(db: Session, row: Dict[str, str]) -> DraftProspect:
    draft_year = int(row["draft_year"])
    full_name = row["full_name"].strip()
    normalized = normalize_name(full_name)
    external_id = "historical-{0}-{1}".format(draft_year, normalized.replace(" ", "-"))

    existing = (
        db.query(DraftProspect)
        .filter(
            DraftProspect.draft_year == draft_year,
            DraftProspect.external_id == external_id,
        )
        .one_or_none()
    )
    p = existing or DraftProspect(
        draft_year=draft_year,
        external_id=external_id,
        full_name=full_name,
    )
    p.full_name = full_name
    p.draft_year = draft_year
    p.school = row.get("school") or p.school
    p.primary_position = row.get("primary_position") or p.primary_position
    p.draft_pick_number = _to_int(row.get("draft_pick"))
    p.is_historical = True
    if existing is None:
        db.add(p)
        db.flush()
    return p


def _upsert_outcome(
    db: Session,
    prospect: DraftProspect,
    row: Dict[str, str],
    player_id: Optional[int],
) -> bool:
    existing = (
        db.query(DraftOutcome)
        .filter(
            DraftOutcome.prospect_id == prospect.id,
            DraftOutcome.draft_year == prospect.draft_year,
        )
        .one_or_none()
    )
    target = existing or DraftOutcome(
        prospect_id=prospect.id, draft_year=prospect.draft_year
    )
    target.player_id = player_id
    target.draft_pick = _to_int(row.get("draft_pick"))
    target.career_games = _to_int(row.get("career_games"))
    target.career_minutes = _to_float(row.get("career_minutes"))
    target.career_ppg = _to_float(row.get("career_ppg"))
    target.career_ws = _to_float(row.get("career_ws"))
    target.career_vorp = _to_float(row.get("career_vorp"))
    target.peak_per = _to_float(row.get("peak_per"))
    target.all_star_selections = _to_int(row.get("all_star_selections")) or 0
    target.all_nba_selections = _to_int(row.get("all_nba_selections")) or 0
    target.as_of_season = _to_int(row.get("as_of_season"))
    target.outcome_tier = classify_outcome(
        career_games=target.career_games,
        career_minutes=target.career_minutes,
        career_ws=target.career_ws,
        all_star_selections=target.all_star_selections,
        all_nba_selections=target.all_nba_selections,
    )
    target.external_metrics_meta = {
        "source": "seed_csv:draft_outcomes_2016_2025",
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
    if existing is None:
        db.add(target)
        return True
    return False


def _upsert_linkage(
    db: Session,
    prospect: DraftProspect,
    player_id: int,
    method: str,
    confidence: float,
) -> None:
    existing = (
        db.query(DraftProspectLinkage)
        .filter(
            DraftProspectLinkage.prospect_id == prospect.id,
            DraftProspectLinkage.player_id == player_id,
        )
        .one_or_none()
    )
    if existing is not None:
        existing.match_method = method
        existing.confidence = confidence
        return
    db.add(DraftProspectLinkage(
        prospect_id=prospect.id,
        player_id=player_id,
        match_method=method,
        confidence=confidence,
    ))


def backfill(
    start_year: int = 2016,
    end_year: int = 2025,
    csv_path: str = DEFAULT_CSV_PATH,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Read seed CSV, upsert prospects + outcomes for years in [start, end]."""
    rows = _read_seed(csv_path)
    if not rows:
        return {"rows": 0, "skipped_out_of_range": 0, "matched": 0, "unmatched": 0}

    db = SessionLocal()
    matched = 0
    unmatched: List[Dict[str, Any]] = []
    inserted_outcomes = 0
    out_of_range = 0
    try:
        for row in rows:
            year = int(row.get("draft_year") or 0)
            if not (start_year <= year <= end_year):
                out_of_range += 1
                continue
            full_name = (row.get("full_name") or "").strip()
            if not full_name:
                continue
            prospect = _upsert_prospect(db, row)
            # Try to link by name; the CSV's ``nba_player_name`` is an
            # explicit override hint if linkage struggles.
            name_for_match = (row.get("nba_player_name") or full_name).strip()
            player_id, method, conf = resolve_player_id(
                db, name_for_match, draft_year=year, position=row.get("primary_position")
            )
            if player_id is not None:
                matched += 1
                _upsert_linkage(db, prospect, player_id, method, conf)
            else:
                unmatched.append({"draft_year": year, "name": full_name})
            inserted = _upsert_outcome(db, prospect, row, player_id)
            if inserted:
                inserted_outcomes += 1

        if dry_run:
            db.rollback()
        else:
            db.commit()
    finally:
        db.close()

    # Report unmatched prospects to a side file for manual fixup.
    if unmatched:
        report_path = os.path.join(os.path.dirname(csv_path), "unmatched_prospects_report.csv")
        try:
            with open(report_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=["draft_year", "name"])
                writer.writeheader()
                for u in unmatched:
                    writer.writerow(u)
            logger.info("backfill_draft_outcomes: %d unmatched written to %s", len(unmatched), report_path)
        except OSError as exc:  # pragma: no cover - non-fatal
            logger.warning("backfill_draft_outcomes: failed to write %s: %s", report_path, exc)

    return {
        "rows": len(rows),
        "in_range": len(rows) - out_of_range,
        "skipped_out_of_range": out_of_range,
        "matched": matched,
        "unmatched": len(unmatched),
        "outcomes_inserted": inserted_outcomes,
        "dry_run": dry_run,
    }


def main(argv: list = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-year", type=int, default=2016)
    parser.add_argument("--end-year", type=int, default=2025)
    parser.add_argument("--source", choices=["seed", "bbref"], default="seed",
                        help="seed = CSV; bbref = Basketball-Reference scrape (NOT IMPLEMENTED)")
    parser.add_argument("--csv-path", default=DEFAULT_CSV_PATH)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.source == "bbref":
        logger.error("--source bbref not yet implemented; use --source seed")
        return 2

    result = backfill(
        start_year=args.start_year,
        end_year=args.end_year,
        csv_path=args.csv_path,
        dry_run=args.dry_run,
    )
    logger.info("backfill_draft_outcomes complete: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
