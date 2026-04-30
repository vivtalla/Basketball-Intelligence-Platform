"""CLI to upsert historical injuries into ``player_injury_history``.

Sprint 78 FO5 — backs the Injury Duration Model.
Sprint 81 — adds ``--source prosportstransactions`` for live scraping with
seed-CSV fallback.

Modes:
    --source prosportstransactions  (default; falls back to seed_csv on failure)
    --source seed_csv               (offline-only; reads the synthetic seed)

Run (from ``backend/``):
    python data/sync_injury_history.py --source prosportstransactions --start-date 2020-10-01
    python data/sync_injury_history.py --source seed_csv

Dedupe key: ``(player_id, body_part, started_on)``.
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

# Allow running directly from `backend/` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from db.database import SessionLocal  # noqa: E402
from db.models import Player, PlayerInjuryHistory  # noqa: E402

logger = logging.getLogger(__name__)

SEED_CSV_PATH = Path(__file__).resolve().parent / "seed" / "player_injury_history_seed.csv"

# Default backfill window for PST scrapes — 2020-onward keeps row count
# reasonable (~10k rows) and avoids edge-case date parsing on older filings.
DEFAULT_PST_START_DATE = date(2020, 10, 1)


def _parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_int(value: str) -> Optional[int]:
    value = (value or "").strip()
    if not value:
        return None
    return int(float(value))


def _parse_float(value: str) -> Optional[float]:
    value = (value or "").strip()
    if not value:
        return None
    return float(value)


def _parse_bool(value: str) -> bool:
    return (value or "").strip().lower() in {"true", "1", "yes", "y"}


def _normalize_body_part(value: str) -> str:
    return (value or "").strip().lower().replace("_", "-")


def _build_player_index(db: Session) -> Dict[str, int]:
    """Lowercase full-name → player_id."""
    return {
        (p.full_name or "").strip().lower(): p.id
        for p in db.query(Player).all()
        if p.full_name
    }


def _upsert_injury_row(
    db: Session,
    *,
    player_id: int,
    season: Optional[str],
    body_part: str,
    severity: Optional[str],
    diagnosis: Optional[str],
    started_on: date,
    resolved_on: Optional[date],
    games_missed: Optional[int],
    age_at_start: Optional[float],
    is_recurring: bool,
    source: str,
    source_url: Optional[str] = None,
) -> str:
    """Upsert one row. Returns 'inserted' / 'updated' / 'unchanged'."""
    existing = (
        db.query(PlayerInjuryHistory)
        .filter(
            PlayerInjuryHistory.player_id == player_id,
            PlayerInjuryHistory.body_part == body_part,
            PlayerInjuryHistory.started_on == started_on,
        )
        .first()
    )

    if existing is None:
        db.add(
            PlayerInjuryHistory(
                player_id=player_id,
                season=season,
                body_part=body_part,
                severity=severity,
                diagnosis=diagnosis,
                started_on=started_on,
                resolved_on=resolved_on,
                games_missed=games_missed,
                age_at_start=age_at_start,
                is_recurring=is_recurring,
                source=source,
                source_url=source_url,
            )
        )
        return "inserted"

    changed = False
    for field, new_value in (
        ("season", season),
        ("severity", severity),
        ("diagnosis", diagnosis),
        ("resolved_on", resolved_on),
        ("games_missed", games_missed),
        ("age_at_start", age_at_start),
        ("is_recurring", is_recurring),
        ("source", source),
        ("source_url", source_url),
    ):
        if new_value is not None and getattr(existing, field) != new_value:
            setattr(existing, field, new_value)
            changed = True
    return "updated" if changed else "unchanged"


def upsert_seed_csv(
    db: Session,
    csv_path: Path = SEED_CSV_PATH,
    *,
    verbose: bool = True,
) -> Dict[str, Any]:
    if not csv_path.exists():
        raise FileNotFoundError(
            "Seed CSV not found at {0}".format(csv_path)
        )

    known_player_ids = {row[0] for row in db.query(Player.id).all()}

    inserted = updated = skipped_unknown_player = skipped_invalid = 0

    with csv_path.open("r", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            try:
                player_id = int(raw["player_id"])
                started_on = _parse_date(raw["started_on"])
                if started_on is None:
                    skipped_invalid += 1
                    continue
                body_part = _normalize_body_part(raw["body_part"])
            except (KeyError, ValueError):
                skipped_invalid += 1
                continue

            if player_id not in known_player_ids:
                skipped_unknown_player += 1
                continue

            outcome = _upsert_injury_row(
                db,
                player_id=player_id,
                season=(raw.get("season") or "").strip() or None,
                body_part=body_part,
                severity=(raw.get("severity") or "").strip().lower() or None,
                diagnosis=None,
                started_on=started_on,
                resolved_on=_parse_date(raw.get("resolved_on", "")),
                games_missed=_parse_int(raw.get("games_missed", "")),
                age_at_start=_parse_float(raw.get("age_at_start", "")),
                is_recurring=_parse_bool(raw.get("is_recurring", "false")),
                source=(raw.get("source") or "seed_synthetic").strip(),
                source_url=None,
            )
            if outcome == "inserted":
                inserted += 1
            elif outcome == "updated":
                updated += 1

    db.commit()
    summary = {
        "inserted": inserted,
        "updated": updated,
        "skipped_unknown_player": skipped_unknown_player,
        "skipped_invalid": skipped_invalid,
        "csv_path": str(csv_path),
        "source": "seed_csv",
    }
    if verbose:
        print("sync_injury_history seed summary:", summary)
    return summary


def _fetch_pst_rows(start_date: date, end_date: date) -> List[Dict[str, Any]]:
    """Live PST scrape; raises ScraperError on failure."""
    from data.scrapers.prosportstransactions import ProSportsTransactionsScraper

    return ProSportsTransactionsScraper().fetch_injuries(
        start_date=start_date, end_date=end_date
    )


def upsert_from_prosportstransactions(
    db: Session,
    *,
    start_date: date = DEFAULT_PST_START_DATE,
    end_date: Optional[date] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Live-scrape PST and upsert; falls back to seed CSV on any failure."""
    end_date = end_date or date.today()
    name_index = _build_player_index(db)

    try:
        raw_rows = _fetch_pst_rows(start_date, end_date)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "PST scrape failed (%s) — falling back to seed CSV", exc
        )
        result = upsert_seed_csv(db, csv_path=SEED_CSV_PATH, verbose=verbose)
        result["fallback_used"] = True
        result["pst_error"] = str(exc)
        return result

    if not raw_rows:
        logger.warning("PST returned 0 rows — falling back to seed CSV")
        result = upsert_seed_csv(db, csv_path=SEED_CSV_PATH, verbose=verbose)
        result["fallback_used"] = True
        return result

    inserted = updated = skipped_unknown_player = skipped_invalid = 0

    for row in raw_rows:
        name = (row.get("player_name") or "").strip().lower()
        player_id = name_index.get(name)
        if player_id is None:
            skipped_unknown_player += 1
            continue
        started_on = row.get("started_on")
        if not isinstance(started_on, date):
            skipped_invalid += 1
            continue

        from data.scrapers.prosportstransactions import _season_for
        season = _season_for(started_on)

        resolved_on = row.get("resolved_on")
        games_missed: Optional[int] = None
        if isinstance(resolved_on, date):
            # Rough proxy: assume ~3.5 games/week NBA cadence.
            days = (resolved_on - started_on).days
            if days > 0:
                games_missed = max(1, int(round(days * 0.5)))

        outcome = _upsert_injury_row(
            db,
            player_id=player_id,
            season=season,
            body_part=row.get("body_part") or "other",
            severity=row.get("severity"),
            diagnosis=row.get("diagnosis"),
            started_on=started_on,
            resolved_on=resolved_on,
            games_missed=games_missed,
            age_at_start=None,
            is_recurring=False,  # could enrich from prior rows in a follow-up
            source="prosportstransactions",
            source_url="https://prosportstransactions.com/basketball/Search/SearchResults.php",
        )
        if outcome == "inserted":
            inserted += 1
        elif outcome == "updated":
            updated += 1

    db.commit()
    summary = {
        "inserted": inserted,
        "updated": updated,
        "skipped_unknown_player": skipped_unknown_player,
        "skipped_invalid": skipped_invalid,
        "source": "prosportstransactions",
        "fallback_used": False,
        "window": "{0}..{1}".format(start_date.isoformat(), end_date.isoformat()),
    }
    if verbose:
        print("sync_injury_history PST summary:", summary)
    return summary


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert historical injuries.")
    parser.add_argument(
        "--source",
        choices=["seed_csv", "prosportstransactions"],
        default="prosportstransactions",
        help="Data source. Defaults to PST live scrape (falls back to seed_csv on error).",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=SEED_CSV_PATH,
        help="Override path to the seed CSV.",
    )
    parser.add_argument(
        "--start-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=DEFAULT_PST_START_DATE,
        help="Earliest injury date to ingest from PST (default 2020-10-01).",
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=None,
        help="Latest injury date (default: today).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    db = SessionLocal()
    try:
        if args.source == "seed_csv":
            upsert_seed_csv(db, args.csv_path)
        else:
            upsert_from_prosportstransactions(
                db, start_date=args.start_date, end_date=args.end_date
            )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
