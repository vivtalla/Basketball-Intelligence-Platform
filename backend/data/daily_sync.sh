#!/bin/bash
set -e
cd "$(dirname "$0")/.."

SEASON="${1:-2024-25}"
LOG=/var/log/bip_sync.log

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync start season=$SEASON" >> "$LOG"

# 1. Warehouse ingestion jobs (schedule, box scores, PBP, materialization)
python data/warehouse_jobs.py --season "$SEASON" --max-jobs 100 >> "$LOG" 2>&1

# 2. Injuries sync — queue a sync_injuries job for today
python - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from db.database import SessionLocal
from services.sync_service import sync_injuries
db = SessionLocal()
try:
    result = sync_injuries(db, season="$SEASON")
    print("sync_injuries:", result)
finally:
    db.close()
PYEOF

# 3. Materialize standings
python - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
from db.database import SessionLocal
from services.standings_service import materialize_standings
db = SessionLocal()
try:
    result = materialize_standings(season="$SEASON", db=db)
    print("materialize_standings:", result)
finally:
    db.close()
PYEOF

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync complete season=$SEASON" >> "$LOG"
