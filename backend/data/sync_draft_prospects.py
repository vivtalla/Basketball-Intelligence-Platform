"""Sprint 78 / FO3 — Draft Prospect ingestion CLI.

Loads a curated seed CSV of draft-eligible prospects (no live Sports
Reference scraping in this sprint) and upserts them into:

- ``draft_prospects`` (one row per prospect)
- ``draft_prospect_stats`` (one row per prospect-season-league)
- ``draft_prospect_measurements`` (one lightweight row per prospect, derived
  from listed height/weight + the optional ``wingspan`` column)

Usage::

    python data/sync_draft_prospects.py --source seed_csv
    python data/sync_draft_prospects.py --source seed_csv --year 2026
    python data/sync_draft_prospects.py --source seed_csv \
        --csv-path data/seed/draft_prospects_2026.csv

The script is idempotent — re-running it updates fields in place rather than
creating duplicates. ``daily_sync.sh`` invokes the seed-CSV path so the board
populates after a fresh DB.
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from typing import Optional

from sqlalchemy.orm import Session

# Allow `python data/sync_draft_prospects.py` to work when run from `backend/`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal
from db.models import DraftProspect, DraftProspectMeasurement, DraftProspectStat

logger = logging.getLogger(__name__)

# NCAA D-I mens' season pace converged to ~70 possessions/40 over the past
# few seasons. Stored on each stat row so the translation service can pull it
# without re-deriving from the league string.
DEFAULT_NCAA_PACE = 70.0
DEFAULT_GLEAGUE_PACE = 100.0
DEFAULT_INTL_PACE = 76.0  # Euroleague / Adriatic ~ 75-78

LEAGUE_PACE_MAP = {
    "ncaa": DEFAULT_NCAA_PACE,
    "g_league": DEFAULT_GLEAGUE_PACE,
    "international": DEFAULT_INTL_PACE,
    "high_school": DEFAULT_NCAA_PACE,
}

LEAGUE_LABEL_MAP = {
    "ncaa": "NCAA D-I",
    "g_league": "G League",
    "international": "International",
    "high_school": "High School",
}

DEFAULT_CSV_PATH = "data/seed/draft_prospects_2026.csv"


def _to_float(raw: Optional[str]) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _to_int(raw: Optional[str]) -> Optional[int]:
    f = _to_float(raw)
    if f is None:
        return None
    return int(f)


def _upsert_prospect(db: Session, row: dict, draft_year: int) -> DraftProspect:
    external_id = row["external_id"].strip()
    school_type = (row.get("school_type") or "ncaa").strip()
    prospect = (
        db.query(DraftProspect)
        .filter(
            DraftProspect.draft_year == draft_year,
            DraftProspect.external_id == external_id,
        )
        .one_or_none()
    )
    if prospect is None:
        prospect = DraftProspect(
            external_id=external_id,
            draft_year=draft_year,
        )
        db.add(prospect)

    prospect.full_name = row["full_name"].strip()
    prospect.age_on_draft_day = _to_float(row.get("age"))
    prospect.height_inches = _to_float(row.get("height_inches"))
    prospect.weight_lbs = _to_float(row.get("weight_lbs"))
    prospect.primary_position = (row.get("primary_position") or "").strip() or None
    prospect.school = (row.get("school") or "").strip() or None
    prospect.school_type = school_type or None
    prospect.consensus_rank = _to_int(row.get("consensus_rank"))
    prospect.consensus_sources = {"seed_csv": prospect.consensus_rank} if prospect.consensus_rank else {}
    db.flush()
    return prospect


def _upsert_stat(db: Session, prospect: DraftProspect, row: dict, season: str) -> DraftProspectStat:
    school_type = prospect.school_type or "ncaa"
    league = LEAGUE_LABEL_MAP.get(school_type, "NCAA D-I")
    pace = LEAGUE_PACE_MAP.get(school_type, DEFAULT_NCAA_PACE)

    stat = (
        db.query(DraftProspectStat)
        .filter(
            DraftProspectStat.prospect_id == prospect.id,
            DraftProspectStat.season == season,
            DraftProspectStat.league == league,
        )
        .one_or_none()
    )
    if stat is None:
        stat = DraftProspectStat(
            prospect_id=prospect.id,
            season=season,
            league=league,
        )
        db.add(stat)

    stat.team_name = prospect.school
    stat.gp = 30  # plausible NCAA-D1 sample; seed CSV omits raw counts
    stat.min_pg = 30.0
    stat.pts_pg = _to_float(row.get("ppg"))
    stat.reb_pg = _to_float(row.get("rpg"))
    stat.ast_pg = _to_float(row.get("apg"))
    stat.fg_pct = _to_float(row.get("fg_pct"))
    stat.fg3_pct = _to_float(row.get("fg3_pct"))
    stat.ts_pct = _to_float(row.get("ts_pct"))
    stat.usg_pct = _to_float(row.get("usg_pct"))
    stat.pace = pace
    stat.source = "seed_csv"
    db.flush()
    return stat


def _upsert_measurement(db: Session, prospect: DraftProspect, row: dict) -> Optional[DraftProspectMeasurement]:
    height = _to_float(row.get("height_inches"))
    weight = _to_float(row.get("weight_lbs"))
    wingspan = _to_float(row.get("wingspan"))
    # Seed CSV doesn't carry combine-quality measurements — only persist a row
    # when at least one numeric field is present so the panel has something to
    # render.
    if height is None and weight is None and wingspan is None:
        return None

    meas = (
        db.query(DraftProspectMeasurement)
        .filter(DraftProspectMeasurement.prospect_id == prospect.id)
        .one_or_none()
    )
    if meas is None:
        meas = DraftProspectMeasurement(
            prospect_id=prospect.id,
            source="seed_csv",
        )
        db.add(meas)

    meas.height_with_shoes = height
    meas.height_no_shoes = (height - 1.0) if height is not None else None
    meas.weight = weight
    meas.wingspan = wingspan
    db.flush()
    return meas


def sync_seed_csv(db: Session, csv_path: str, draft_year: int, season: str) -> dict:
    """Upsert prospects + stats + measurements from a seed CSV. Returns a counts dict."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Seed CSV not found: {csv_path}")

    counts = {"prospects": 0, "stats": 0, "measurements": 0}
    with open(csv_path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row = {k: (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
            prospect = _upsert_prospect(db, row, draft_year)
            counts["prospects"] += 1
            _upsert_stat(db, prospect, row, season)
            counts["stats"] += 1
            if _upsert_measurement(db, prospect, row) is not None:
                counts["measurements"] += 1

    db.commit()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["seed_csv"], default="seed_csv",
                        help="Ingestion source (only seed_csv is wired this sprint).")
    parser.add_argument("--csv-path", default=DEFAULT_CSV_PATH,
                        help="Path to seed CSV (relative to backend/).")
    parser.add_argument("--year", type=int, default=2026,
                        help="Draft year (default: 2026).")
    parser.add_argument("--season", default="2025-26",
                        help="Pre-draft season string for stat rows.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db = SessionLocal()
    try:
        counts = sync_seed_csv(db, args.csv_path, args.year, args.season)
        logger.info("draft prospect sync complete: %s", counts)
        print(f"sync_draft_prospects: {counts}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
