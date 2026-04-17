#!/bin/bash
set -e
cd "$(dirname "$0")/.."

if [ -n "$1" ]; then
  SEASON="$1"
else
  SEASON="$(python - <<'PYEOF'
from datetime import datetime

now = datetime.utcnow()
start_year = now.year if now.month >= 8 else now.year - 1
print(f"{start_year}-{str((start_year + 1) % 100).zfill(2)}")
PYEOF
)"
fi
export SEASON
LOG="$HOME/Library/Logs/bip_sync.log"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync start season=$SEASON" >> "$LOG"

# 1. Queue current-season shot chart refresh work
python - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.warehouse_service import queue_season_shot_charts
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    jobs = queue_season_shot_charts(db, season=season, season_type="Regular Season", force=False)
    db.commit()
    print("queue_season_shot_charts:", {"queued": len(jobs), "job_types": [job.job_type for job in jobs]})
finally:
    db.close()
PYEOF

# 2. Warehouse ingestion jobs (schedule, box scores, PBP, materialization, shot charts)
python data/warehouse_jobs.py --season "$SEASON" --max-jobs 100 >> "$LOG" 2>&1

# 3. Injuries sync — queue a sync_injuries job for today
python - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.sync_service import sync_injuries
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    result = sync_injuries(db, season=season)
    print("sync_injuries:", result)
finally:
    db.close()
PYEOF

# 4. Materialize standings
python - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.standings_service import materialize_standings
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    result = materialize_standings(season=season, db=db)
    print("materialize_standings:", result)
finally:
    db.close()
PYEOF

# 5. Refresh official player and team season dashboards
python - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.sync_service import sync_official_season_stats, sync_official_team_general_splits, sync_official_team_season_stats
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    print("sync_official_season_stats:", sync_official_season_stats(db, season=season))
    print("sync_official_team_season_stats:", sync_official_team_season_stats(db, season=season))
    print("sync_official_team_general_splits:", sync_official_team_general_splits(db, season=season))
finally:
    db.close()
PYEOF

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync complete season=$SEASON" >> "$LOG"
