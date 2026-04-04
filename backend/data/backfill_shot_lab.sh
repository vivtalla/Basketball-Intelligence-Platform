#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

SEASONS=("2022-23" "2023-24" "2024-25" "2025-26")

for season in "${SEASONS[@]}"; do
  echo
  echo "=== Shot lab backfill: ${season} regular season ==="
  python data/bulk_import.py --season "$season" --shot-charts --season-type "Regular Season" --force

  echo
  echo "=== Shot lab backfill: ${season} playoffs ==="
  python data/bulk_import.py --season "$season" --shot-charts --season-type "Playoffs" --force
done
