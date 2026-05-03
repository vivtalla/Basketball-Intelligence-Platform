#!/bin/bash
# CourtVue Labs — weekly sync (Sprint 88 Stream A).
#
# Heavier ops that don't need to run nightly:
#  - Player tracking dashboards: ~450 NBA API calls (1 per player), ~5 min
#    wall-clock at 0.6s rate-limit. Once per week is enough for the player
#    profile Tracking panel to show fresh data.
#
# Invoked by /etc/crontab (see infra/cron.txt) Sundays at 8am UTC, after the
# 6am daily_sync settles. Logs to /var/log/bip-sync.log alongside daily_sync.

set -euo pipefail

cd /home/ubuntu/bip/backend
LOG="/var/log/bip-sync.log"
PYTHON_BIN="/home/ubuntu/bip/backend/venv/bin/python"
SEASON="${SEASON:-2025-26}"
SEASON_TYPE="${SEASON_TYPE:-Regular Season}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] weekly_sync start season=$SEASON season_type=\"$SEASON_TYPE\"" >> "$LOG"

# Ensure cron context can hit nba_api (override the user-fetch guard for sync).
export NBA_API_USER_FETCH_DISABLED=false

"$PYTHON_BIN" - <<PYEOF >> "$LOG" 2>&1
import os, sys
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.gravity_sync_service import sync_player_tracking_stats

season = os.environ.get("SEASON", "2025-26")
season_type = os.environ.get("SEASON_TYPE", "Regular Season")
db = SessionLocal()
try:
    # player_ids=None → all active players for (season, season_type) per
    # PlayerGameLog; ~450 calls × 0.6s rate-limit ≈ 5 min.
    print("sync_player_tracking_stats:", sync_player_tracking_stats(
        db, season=season, season_type=season_type
    ))
finally:
    db.close()
PYEOF

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] weekly_sync complete season=$SEASON" >> "$LOG"
