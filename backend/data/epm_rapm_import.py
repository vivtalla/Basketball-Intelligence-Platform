"""Import external player metrics from CSV into SeasonStat table.

Supports any metric column stored in season_stats. Common use cases:
  python epm_rapm_import.py data.csv --metrics epm,rapm
  python epm_rapm_import.py data.csv --metrics lebron
  python epm_rapm_import.py data.csv --metrics raptor,pipm,lebron

Expected CSV columns: player_id, season, <metric1>, <metric2>, ...

Public data sources:
  LEBRON  — https://www.bball-index.com/lebron-introduction/
  RAPTOR  — https://github.com/fivethirtyeight/data/tree/master/nba-raptor
  PIPM    — https://www.bball-index.com/player-impact-plus-minus/
  EPM     — https://dunksandthrees.com/epm
  RAPM    — https://nbarapm.com/
"""
import csv
import os
import sys
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import SeasonStat

# All metric columns supported for import
SUPPORTED_METRICS = {"epm", "rapm", "lebron", "raptor", "pipm"}


def import_metrics(csv_path: str, metrics: list[str], batch_size: int = 100) -> dict:
    """Import one or more metric columns from a CSV file.

    Args:
        csv_path: Path to the CSV file.
        metrics: List of metric column names to import (e.g. ["lebron", "raptor"]).
        batch_size: Number of rows to commit per batch.

    Returns:
        Dict with counts: {"updated": N, "skipped": N, "not_found": N}
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    unknown = set(metrics) - SUPPORTED_METRICS
    if unknown:
        raise ValueError(
            f"Unsupported metric(s): {unknown}. "
            f"Supported: {sorted(SUPPORTED_METRICS)}"
        )

    session: Session = SessionLocal()
    counts = {"updated": 0, "skipped": 0, "not_found": 0}

    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                player_id = int(row.get("player_id") or 0)
            except ValueError:
                counts["skipped"] += 1
                continue

            season = (row.get("season") or "").strip()
            if not player_id or not season:
                counts["skipped"] += 1
                continue

            stat = (
                session.query(SeasonStat)
                .filter(
                    SeasonStat.player_id == player_id,
                    SeasonStat.season == season,
                    SeasonStat.is_playoff == False,  # noqa: E712
                )
                .first()
            )
            if not stat:
                counts["not_found"] += 1
                continue

            for metric in metrics:
                raw = row.get(metric)
                value = float(raw) if raw not in (None, "", "NA", "N/A", "null") else None
                setattr(stat, metric, value)

            counts["updated"] += 1
            if counts["updated"] % batch_size == 0:
                session.commit()

    session.commit()
    session.close()
    return counts


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Import external player metrics from CSV into season_stats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("csv_path", help="Path to the CSV file")
    parser.add_argument(
        "--metrics",
        default="epm,rapm",
        help=f"Comma-separated metric columns to import. Supported: {sorted(SUPPORTED_METRICS)} (default: epm,rapm)",
    )
    args = parser.parse_args()

    metric_list = [m.strip().lower() for m in args.metrics.split(",") if m.strip()]
    if not metric_list:
        print("Error: --metrics must specify at least one metric.", file=sys.stderr)
        sys.exit(1)

    try:
        result = import_metrics(args.csv_path, metric_list)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(
        f"Done. Updated: {result['updated']} rows | "
        f"Not found in DB: {result['not_found']} | "
        f"Skipped (bad data): {result['skipped']}"
    )
