#!/bin/bash
#
# CourtVue Labs — daily / post-game data sync orchestrator.
#
# Recommended cron lines (replace /path/to/repo with the absolute repo path):
#
#   # Daily full sync — 6am UTC. Picks up yesterday's late finals + runs the
#   # full pipeline (warehouse jobs, standings, season dashboards, playoff
#   # slice when in season).
#   0 6 * * * /path/to/repo/backend/data/daily_sync.sh
#
#   # Post-game refresh — every 30 minutes. Cheap. Self-gates on the season
#   # phase, so outside the playoff window it's near-zero work. During the
#   # postseason it ingests today's final-status games from the live CDN
#   # scoreboard, recomputes the bracket, and refreshes injuries + splits.
#   */30 * * * * /path/to/repo/backend/data/daily_sync.sh --post-game
#
# Manual usage:
#   ./daily_sync.sh                  # full daily run, current season auto-detected
#   ./daily_sync.sh --post-game      # lightweight refresh
#   ./daily_sync.sh --dry-run        # print intended actions, do nothing
#   ./daily_sync.sh 2025-26          # explicit season override
#
set -e
cd "$(dirname "$0")/.."

# ---------------------------------------------------------------------------
# Argument parsing — `--post-game` runs the lightweight playoff-night refresh
# (game logs, brackets, splits, injuries) and exits. `--dry-run` just prints
# what each path *would* do and exits 0.
# ---------------------------------------------------------------------------
POST_GAME_MODE=0
DRY_RUN=0
SEASON=""

for arg in "$@"; do
  case "$arg" in
    --post-game) POST_GAME_MODE=1 ;;
    --dry-run)   DRY_RUN=1 ;;
    --*)         echo "warning: unknown flag $arg" >&2 ;;
    *)
      if [ -z "$SEASON" ]; then
        SEASON="$arg"
      fi
      ;;
  esac
done

# Resolve the python interpreter once. Prefer the project venv when present
# (matches how the existing daily cron runs), otherwise fall back to the
# system `python` or `python3` so manual / dry-run invocations succeed in
# minimal environments.
if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x "./venv/bin/python" ]; then
    PYTHON_BIN="./venv/bin/python"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    PYTHON_BIN="python3"
  fi
fi
export PYTHON_BIN

if [ -z "$SEASON" ]; then
  SEASON="$("$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || true
from datetime import datetime

now = datetime.utcnow()
start_year = now.year if now.month >= 8 else now.year - 1
print(f"{start_year}-{str((start_year + 1) % 100).zfill(2)}")
PYEOF
)"
  if [ -z "$SEASON" ]; then
    # Fall back to a static current season string so the script remains
    # usable when no python interpreter is available (e.g. dry-run on a
    # bare CI worker). Cron callers should always pass an explicit season.
    SEASON="2025-26"
  fi
fi
export SEASON

# ---------------------------------------------------------------------------
# Detect playoff window via the season-phase service. Falls back to an
# April–June heuristic if the service module is unavailable so dry-runs
# stay deterministic.
# ---------------------------------------------------------------------------
IS_PLAYOFFS="$("$PYTHON_BIN" - <<'PYEOF' 2>/dev/null || echo 0
import sys, os
sys.path.insert(0, os.getcwd())
phase = ""
try:
    from services.season_phase_service import get_current_phase  # type: ignore
    phase = (getattr(get_current_phase(), "phase", "") or "")
except Exception:
    from datetime import datetime
    month = datetime.utcnow().month
    if 4 <= month <= 6:
        phase = "playoff_round_1"
print("1" if str(phase).startswith("playoff") else "0")
PYEOF
)"
if [ -z "$IS_PLAYOFFS" ]; then
  IS_PLAYOFFS=0
fi
export IS_PLAYOFFS

LOG="$HOME/Library/Logs/bip_sync.log"

# Track summary counters for the closing log line.
SERIES_REFRESHED="${SERIES_REFRESHED:-0}"
GAMES_REFRESHED="${GAMES_REFRESHED:-0}"

# ---------------------------------------------------------------------------
# Dry-run shortcut: print intended actions and exit before doing real work.
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = "1" ]; then
  echo "daily_sync dry-run: season=$SEASON post_game=$POST_GAME_MODE is_playoffs=$IS_PLAYOFFS"
  if [ "$POST_GAME_MODE" = "1" ]; then
    echo "would run: ingest today's playoff finals from CDN scoreboard"
    echo "would run: playoff game-log refresh"
    echo "would run: bracket refreshed"
    echo "would run: sync_injuries"
    echo "would run: sync_official_team_general_splits is_playoff=True"
    echo "would run: sync_official_team_shooting_splits is_playoff=True"
  else
    echo "would run: queue_season_shot_charts"
    echo "would run: warehouse_jobs"
    echo "would run: sync_injuries"
    echo "would run: materialize_standings"
    echo "would run: sync_official_season_stats"
    echo "would run: sync_official_team_season_stats"
    echo "would run: sync_official_team_general_splits"
    echo "would run: sync_official_team_shooting_splits"
    if [ "$IS_PLAYOFFS" = "1" ]; then
      echo "would run: ingest today's playoff finals from CDN scoreboard"
      echo "would run: playoff sync_official_season_stats is_playoff=True"
      echo "would run: playoff sync_official_team_general_splits is_playoff=True"
      echo "would run: playoff sync_official_team_shooting_splits is_playoff=True"
      echo "would run: bracket refreshed"
    fi
  fi
  echo "daily_sync dry-run complete: series_refreshed=$SERIES_REFRESHED games_refreshed=$GAMES_REFRESHED"
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync start season=$SEASON post_game=$POST_GAME_MODE is_playoffs=$IS_PLAYOFFS" >> "$LOG"

# ---------------------------------------------------------------------------
# Post-game cron path: minimal refresh after each playoff game.
# ---------------------------------------------------------------------------
if [ "$POST_GAME_MODE" = "1" ]; then
  # Step 0 — ingest any final-status playoff games from the live CDN
  # scoreboard that aren't yet in GameLog. Without this, the bracket
  # recompute below sees stale series state. Non-fatal if it fails:
  # the rest of the pipeline still runs against whatever's in the DB.
  PYTHONPATH=. "$PYTHON_BIN" data/sync_today_playoff_finals.py --season "$SEASON" >> "$LOG" 2>&1 || true

  "$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1
import os, sys
sys.path.insert(0, os.getcwd())
from datetime import date

from db.database import SessionLocal
from db.models import GameLog
from services.playoff_bracket_service import build_or_refresh_bracket
from services.sync_service import (
    sync_injuries,
    sync_official_team_general_splits,
    sync_official_team_shooting_splits,
)

season = os.environ.get("SEASON", "2024-25")
games_refreshed = 0
series_refreshed = 0
db = SessionLocal()
try:
    today = date.today()
    todays_games_query = db.query(GameLog).filter(GameLog.game_date == today, GameLog.season == season)
    if hasattr(GameLog, "season_type"):
        todays_games_query = todays_games_query.filter(GameLog.season_type == "Playoffs")
    games_refreshed = todays_games_query.count()
    print("post_game: today_playoff_games=", games_refreshed)

    series_refreshed = build_or_refresh_bracket(db, season)
    print("bracket refreshed:", series_refreshed)

    print("sync_injuries:", sync_injuries(db, season=season))
    print("sync_official_team_general_splits playoff:", sync_official_team_general_splits(db, season=season, is_playoff=True))
    print("sync_official_team_shooting_splits playoff:", sync_official_team_shooting_splits(db, season=season, is_playoff=True))
finally:
    db.close()
print("daily_sync_summary: series_refreshed=", series_refreshed, "games_refreshed=", games_refreshed)
PYEOF
  # Post-game also pulls box scores + Synergy/hustle for the game that just
  # finished so the MVP composite + leaderboards reflect tonight's outcome.
  # --fast skips the slow per-player tracking dashboard pass; that runs in
  # the morning daily sync.
  PYTHONPATH=. "$PYTHON_BIN" scripts/sync_playoff_full.py --fast "$SEASON" >> "$LOG" 2>&1 || true
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync post-game complete season=$SEASON" >> "$LOG"
  echo "daily_sync post-game complete: season=$SEASON"
  exit 0
fi

# 1. Queue current-season shot chart refresh work
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1
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
"$PYTHON_BIN" data/warehouse_jobs.py --season "$SEASON" --max-jobs 100 >> "$LOG" 2>&1

# 3. Injuries sync — queue a sync_injuries job for today
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1
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
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1
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

# 5. Refresh official player and team season dashboards (regular-season slice)
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.sync_service import (
    sync_official_season_stats,
    sync_official_team_general_splits,
    sync_official_team_season_stats,
    sync_official_team_shooting_splits,
)
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    print("sync_official_season_stats:", sync_official_season_stats(db, season=season))
    print("sync_official_team_season_stats:", sync_official_team_season_stats(db, season=season))
    print("sync_official_team_general_splits:", sync_official_team_general_splits(db, season=season))
    print("sync_official_team_shooting_splits:", sync_official_team_shooting_splits(db, season=season))
finally:
    db.close()
PYEOF

# 6. Playoff slice — only when the season-phase service reports an active
#    postseason. First catches any final-status games from the live CDN
#    scoreboard that haven't been ingested yet (yesterday's late finals,
#    afternoon games on West Coast, etc.); then delegates to
#    scripts/sync_playoff_full.py which orchestrates:
#      - season_stats / team general+shooting splits with is_playoff=True
#      - GameLog backfill via LeagueGameFinder + bracket refresh
#      - PlayerGameLog from CDN box scores for each playoff game
#      - Synergy play-type, league hustle, per-player tracking dashboards
#    Both legs are idempotent — safe to re-run on every cron tick.
if [ "$IS_PLAYOFFS" = "1" ]; then
  PYTHONPATH=. "$PYTHON_BIN" data/sync_today_playoff_finals.py --season "$SEASON" >> "$LOG" 2>&1 || true
  PYTHONPATH=. "$PYTHON_BIN" scripts/sync_playoff_full.py "$SEASON" >> "$LOG" 2>&1 || true
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync complete season=$SEASON post_game=$POST_GAME_MODE is_playoffs=$IS_PLAYOFFS" >> "$LOG"
