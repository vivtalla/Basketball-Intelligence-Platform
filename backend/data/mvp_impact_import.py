"""Sprint 52 — MVP external impact metrics ingestion.

Thin orchestrator around `epm_rapm_import.import_metrics` that injects curated
source/as-of attribution per metric. Operators still provide local CSVs for
licensed metrics (EPM, LEBRON, PIPM, DARKO); RAPTOR can be fetched directly
from the public 538 GitHub archive.

Examples:
  # local CSV with EPM rows from Dunks & Threes
  python data/mvp_impact_import.py --csv epm.csv --metrics epm

  # fetch RAPTOR archive from 538 for a historical season
  python data/mvp_impact_import.py --fetch-raptor --season 2022-23

  # bulk — one CSV with multiple columns
  python data/mvp_impact_import.py --csv allmetrics.csv --metrics epm,lebron,pipm
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import tempfile
import urllib.request
from datetime import date
from typing import Optional

from data.epm_rapm_import import SUPPORTED_METRICS, import_metrics


METRIC_SOURCES = {
    "epm": "Dunks & Threes — dunksandthrees.com/epm",
    "lebron": "BBall-Index — bball-index.com/lebron-introduction",
    "raptor": "FiveThirtyEight (archived) — github.com/fivethirtyeight/data/tree/master/nba-raptor",
    "pipm": "BBall-Index — bball-index.com/player-impact-plus-minus",
    "darko": "DARKO — apanalytics.shinyapps.io/DARKO",
    "rapm": "nbarapm.com",
}

RAPTOR_CSV_URL = (
    "https://raw.githubusercontent.com/fivethirtyeight/data/master/"
    "nba-raptor/historical_RAPTOR_by_player.csv"
)


def _season_to_raptor_year(season: str) -> int:
    """Convert '2022-23' season string to the 538 `season` integer (2023)."""
    if "-" not in season:
        raise ValueError(f"season must be in 'YYYY-YY' format, got {season!r}")
    start = int(season.split("-")[0])
    return start + 1


def _fetch_raptor_csv(season: str) -> str:
    """Download the 538 RAPTOR archive, filter to one season, return a temp CSV path.

    Output CSV columns: player_id, season, raptor.
    """
    year = _season_to_raptor_year(season)
    with urllib.request.urlopen(RAPTOR_CSV_URL, timeout=30) as resp:
        raw = resp.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(raw))
    # Best available column: raptor_total (predator can be swapped in later).
    out_rows = []
    for row in reader:
        if str(row.get("season", "")) != str(year):
            continue
            # 538 uses BBall-Ref IDs rather than NBA person IDs, so downstream
            # import will rely on the player_id column being pre-joined by the
            # operator. This helper dumps the raw 538 row so the user can map
            # it; a full ID-join script is out of scope for this sprint.
        out_rows.append(
            {
                "player_id": row.get("player_id", ""),  # 538 slug — operator must remap
                "season": season,
                "raptor": row.get("raptor_total", ""),
                "player_name": row.get("player_name", ""),
            }
        )

    if not out_rows:
        raise RuntimeError(
            f"No RAPTOR rows found for season {season} (year={year}). "
            "The 538 archive may not cover this season."
        )

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(tmp, fieldnames=["player_id", "season", "raptor", "player_name"])
    writer.writeheader()
    writer.writerows(out_rows)
    tmp.close()
    print(f"[mvp_impact_import] wrote {len(out_rows)} RAPTOR rows → {tmp.name}")
    print(
        "  NOTE: 538 player_id is a slug, not an NBA person_id. "
        "Operator must remap before importing."
    )
    return tmp.name


def run(
    csv_path: Optional[str],
    metrics: list,
    season: Optional[str] = None,
    fetch_raptor: bool = False,
) -> dict:
    if fetch_raptor:
        if not season:
            raise ValueError("--season is required with --fetch-raptor")
        raptor_csv = _fetch_raptor_csv(season)
        return {
            "fetched": raptor_csv,
            "note": "RAPTOR CSV written locally — remap player_id, then run with --csv/--metrics=raptor",
        }

    if not csv_path:
        raise ValueError("--csv is required unless --fetch-raptor is set")

    # Import each metric with its curated attribution.
    total = {"updated": 0, "skipped": 0, "not_found": 0}
    as_of = date.today().isoformat()
    for metric in metrics:
        if metric not in SUPPORTED_METRICS:
            raise ValueError(f"unsupported metric {metric!r}. Known: {sorted(SUPPORTED_METRICS)}")
        result = import_metrics(
            csv_path,
            [metric],
            source=METRIC_SOURCES.get(metric, metric),
            as_of=as_of,
        )
        for key in total:
            total[key] += result[key]
        print(f"  [{metric}] updated={result['updated']} not_found={result['not_found']}")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--csv", help="CSV path (required unless --fetch-raptor)")
    parser.add_argument("--metrics", default="", help=f"Comma-separated: {sorted(SUPPORTED_METRICS)}")
    parser.add_argument("--season", help="Season e.g. 2025-26 (required with --fetch-raptor)")
    parser.add_argument("--fetch-raptor", action="store_true", help="Download 538 RAPTOR archive")
    args = parser.parse_args()

    metric_list = [m.strip().lower() for m in args.metrics.split(",") if m.strip()]

    try:
        result = run(
            csv_path=args.csv,
            metrics=metric_list,
            season=args.season,
            fetch_raptor=args.fetch_raptor,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Done. {result}")
