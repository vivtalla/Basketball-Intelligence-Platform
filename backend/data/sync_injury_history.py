"""CLI to upsert historical injuries into `player_injury_history`.

Sprint 78 FO5 — backs the Injury Duration Model.

Currently supports a single `--source seed_csv` mode that ingests
`backend/data/seed/player_injury_history_seed.csv` (fabricated-but-realistic
synthetic data — `source` column is `seed_synthetic`). Rows whose `player_id`
is not present in the `players` table are skipped silently so the script is
safe to run on any partially-synced database.

Run (from `backend/`):
    python data/sync_injury_history.py --source seed_csv

# TODO(future): A `--source pst_scrape` mode should ingest a real
# ProSportsTransactions HTML/CSV dump. The contract should match the seed
# CSV header exactly:
#     player_id,season,body_part,severity,started_on,resolved_on,
#     games_missed,age_at_start,is_recurring,source
# `source` should be set to `prosportstransactions` and
# `source_url` to the PST URL of the row. The dedupe key is
# (player_id, body_part, started_on) — same as the seed path.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Optional

# Allow running directly from `backend/` without setting PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session  # noqa: E402

from db.database import SessionLocal  # noqa: E402
from db.models import Player, PlayerInjuryHistory  # noqa: E402


SEED_CSV_PATH = Path(__file__).resolve().parent / "seed" / "player_injury_history_seed.csv"


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


def upsert_seed_csv(
    db: Session,
    csv_path: Path = SEED_CSV_PATH,
    *,
    verbose: bool = True,
) -> dict:
    """Idempotently upsert seed rows. Skips rows for unknown player_ids.

    Dedupe key: (player_id, body_part, started_on).
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            "Seed CSV not found at {0}. Generate it via "
            "`python data/seed/_generate_player_injury_history_seed.py`.".format(csv_path)
        )

    known_player_ids = {row[0] for row in db.query(Player.id).all()}

    inserted = 0
    updated = 0
    skipped_unknown_player = 0
    skipped_invalid = 0

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

            resolved_on = _parse_date(raw.get("resolved_on", ""))
            games_missed = _parse_int(raw.get("games_missed", ""))
            age_at_start = _parse_float(raw.get("age_at_start", ""))
            is_recurring = _parse_bool(raw.get("is_recurring", "false"))
            severity = (raw.get("severity") or "").strip().lower() or None
            season = (raw.get("season") or "").strip() or None
            source = (raw.get("source") or "seed_synthetic").strip() or "seed_synthetic"

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
                        diagnosis=None,
                        started_on=started_on,
                        resolved_on=resolved_on,
                        games_missed=games_missed,
                        age_at_start=age_at_start,
                        is_recurring=is_recurring,
                        source=source,
                        source_url=None,
                    )
                )
                inserted += 1
            else:
                changed = False
                for field, new_value in (
                    ("season", season),
                    ("severity", severity),
                    ("resolved_on", resolved_on),
                    ("games_missed", games_missed),
                    ("age_at_start", age_at_start),
                    ("is_recurring", is_recurring),
                    ("source", source),
                ):
                    if getattr(existing, field) != new_value:
                        setattr(existing, field, new_value)
                        changed = True
                if changed:
                    updated += 1

    db.commit()

    summary = {
        "inserted": inserted,
        "updated": updated,
        "skipped_unknown_player": skipped_unknown_player,
        "skipped_invalid": skipped_invalid,
        "csv_path": str(csv_path),
    }
    if verbose:
        print("sync_injury_history seed summary:", summary)
    return summary


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Upsert historical injuries.")
    parser.add_argument(
        "--source",
        choices=["seed_csv"],
        default="seed_csv",
        help="Data source. Currently only 'seed_csv' is implemented.",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=SEED_CSV_PATH,
        help="Override path to the seed CSV.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    db = SessionLocal()
    try:
        if args.source == "seed_csv":
            upsert_seed_csv(db, args.csv_path)
        else:  # pragma: no cover — argparse already constrains this
            raise SystemExit("Unsupported --source: {0}".format(args.source))
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
