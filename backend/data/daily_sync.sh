#!/bin/bash
#
# CourtVue Labs — daily / post-game data sync orchestrator.
#
# As of Sprint 80 this runs from the Hetzner production VM, not the laptop.
# The canonical crontab lives in `infra/cron.txt` (committed). Operational
# runbook: `specs/db-hosting.md`. To install on a fresh VM:
#
#   crontab /home/ubuntu/bip/infra/cron.txt
#
# That installs:
#   - daily full sync at 6am UTC
#   - post-game refresh every 15 min during the active game window (Sprint 96)
#   - nightly pg_dump → R2 backup at 4am UTC
#   - weekly backup-restore verification on Sunday 5am UTC
#
# Logs land in /var/log/bip-sync.log on the VM (logrotate keeps 14 days).
#
# Manual usage (any environment — laptop dev or VM ops):
#   ./daily_sync.sh                  # full daily run, current season auto-detected
#   ./daily_sync.sh --post-game      # lightweight refresh
#   ./daily_sync.sh --dry-run        # print intended actions, do nothing
#   ./daily_sync.sh 2025-26          # explicit season override
#
set -e
cd "$(dirname "$0")/.."

# Sprint 91 hotfix — fail fast if DATABASE_URL didn't propagate from
# /etc/bip/env. The pre-Sprint-91 cron form (`. /etc/bip/env && bash
# data/daily_sync.sh`) silently dropped exports because the env file is in
# `KEY=value` (no `export`) format; the python subprocesses then crashed
# with `fe_sendauth: no password supplied` and the failure was only visible
# in /var/log/bip-sync.log.
#
# Sprint 97 hardening — self-source /etc/bip/env if it exists and we still
# don't have DATABASE_URL. Production cron lines have been running with
# `set -a && . /etc/bip/env && set +a` for a while, but inspection on
# 2026-05-10 showed every cron firing was hitting the guard anyway —
# something about cron's invocation chain was eating the export. The
# self-source path means the script is robust to that quirk: if the env
# file exists, we'll get the vars regardless of how the caller arranged
# their wrapper.
if [ -z "${DATABASE_URL:-}" ] && [ -f /etc/bip/env ]; then
  set -a
  # shellcheck source=/dev/null
  . /etc/bip/env
  set +a
fi
if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL not set and /etc/bip/env not found. Source it before invoking." >&2
  echo "  set -a && . /etc/bip/env && set +a && bash data/daily_sync.sh" >&2
  exit 1
fi

# Sprint 82d — cron context explicitly allows live NBA API calls. Public-mode
# user-facing requests run with NBA_API_USER_FETCH_DISABLED=true so they only
# read the cache; this export guarantees the nightly sync still fetches live,
# regardless of what /etc/bip/env sets globally.
export NBA_API_USER_FETCH_DISABLED=false

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
  # Script just `cd "$(dirname $0)/.."`-ed up one level (now at backend/), so
  # backend/venv lives at ./venv. The Hetzner VM cwd is /home/ubuntu/bip/backend
  # at this point — same shape. Fall back to ./backend/venv for older laptop
  # layouts where someone invoked the script from the repo root.
  if [ -x "./venv/bin/python" ]; then
    PYTHON_BIN="./venv/bin/python"
  elif [ -x "./backend/venv/bin/python" ]; then
    PYTHON_BIN="./backend/venv/bin/python"
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

# Pick a writable log path. Honor BIP_SYNC_LOG when set; otherwise prefer
# /var/log/bip-sync.log on Linux (where cron also redirects to), fall back
# to the macOS user logs dir for local manual runs, and /tmp as a last resort.
if [ -n "${BIP_SYNC_LOG:-}" ]; then
  LOG="$BIP_SYNC_LOG"
elif [ -w "/var/log/bip-sync.log" ] || { [ -d "/var/log" ] && [ -w "/var/log" ]; }; then
  LOG="/var/log/bip-sync.log"
elif [ -d "$HOME/Library/Logs" ]; then
  LOG="$HOME/Library/Logs/bip_sync.log"
else
  LOG="/tmp/bip-sync.log"
fi

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
    echo "would run: sync_streaks_milestones (CF5 nightly snapshot)"
  else
    echo "would run: queue_season_shot_charts"
    echo "would run: warehouse_jobs"
    echo "would run: sync_injuries"
    echo "would run: sync_injury_history prosportstransactions (S81; falls back to seed CSV)"
    echo "would run: materialize_standings"
    echo "would run: sync_official_season_stats"
    echo "would run: sync_official_team_season_stats"
    echo "would run: sync_official_team_general_splits"
    echo "would run: sync_official_team_shooting_splits"
    echo "would run: sync_official_player_general_splits (S81 B3)"
    echo "would run: sync_official_play_type_stats (S81 B3)"
    echo "would run: sync_role_expansion (S79 A2 — opportunity_v2 uplift dataset)"
    echo "would run: sync_streaks_milestones (CF5 nightly snapshot)"
    echo "would run: sync_salaries spotrac (S81 A1; falls back to seed CSV)"
    echo "would run: sync_draft_prospects sportsreference (S81 A3; falls back to seed CSV)"
    echo "would run: materialize_award_modifiers (S81 B2 — activates mvp_case_v5)"
    if [ "$IS_PLAYOFFS" = "1" ]; then
      echo "would run: ingest today's playoff finals from CDN scoreboard"
      echo "would run: playoff sync_official_season_stats is_playoff=True"
      echo "would run: playoff sync_official_team_general_splits is_playoff=True"
      echo "would run: playoff sync_official_team_shooting_splits is_playoff=True"
      echo "would run: bracket refreshed"
      echo "would run: sync_playoff_pbp (events + on/off + lineup derivations)"
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
from services.playoff_series_backfill import backfill_playoff_series_gaps
from services.regular_season_gap_detector import detect_and_backfill_regular_season_gaps
from services.sync_freshness import record_sync
from services.sync_service import (
    sync_injuries,
    sync_official_team_general_splits,
    sync_official_team_shooting_splits,
)

season = os.environ.get("SEASON", "2024-25")
is_playoffs = os.environ.get("IS_PLAYOFFS") == "1"
games_refreshed = 0
series_refreshed = 0
backfilled_ids = []
rs_backfilled_ids = []
db = SessionLocal()
try:
    today = date.today()
    todays_games_query = db.query(GameLog).filter(GameLog.game_date == today, GameLog.season == season)
    if hasattr(GameLog, "season_type"):
        todays_games_query = todays_games_query.filter(GameLog.season_type == "Playoffs")
    games_refreshed = todays_games_query.count()
    print("post_game: today_playoff_games=", games_refreshed)

    # Sprint 97 — playoff gap-detection backfill. Runs before bracket recompute
    # so the bracket builder sees any newly-recovered games immediately. The
    # service is idempotent: when no gaps exist it does a single NBA probe
    # per active series (~14 calls, ~10s) and returns []. When gaps exist
    # the WARN log lines surface in /var/log/bip-sync.log for monitoring.
    if is_playoffs:
        try:
            backfilled_ids = backfill_playoff_series_gaps(db, season)
            if backfilled_ids:
                print("PLAYOFF BACKFILL recovered", len(backfilled_ids), "missing games:", backfilled_ids)
            else:
                print("playoff backfill: no gaps found")
        except Exception as exc:
            # Non-fatal — log and continue so the rest of the pipeline runs.
            print("playoff backfill failed:", exc)
            try:
                record_sync("playoff_backfill", count=0, source="post_game_cron", error=str(exc)[:200])
            except Exception:
                pass

    # Sprint 98 — regular-season gap detector. Same pattern as the playoff
    # version but walks the CDN season schedule, compares to game_logs, and
    # backfills any final-status game NBA reports that we don't have. Cheap
    # in steady state: 1 schedule fetch + 0 probes when no gaps.
    try:
        rs_backfilled_ids = detect_and_backfill_regular_season_gaps(db, season)
        if rs_backfilled_ids:
            print("RS BACKFILL recovered", len(rs_backfilled_ids), "missing games:", rs_backfilled_ids)
        else:
            print("rs backfill: no gaps found")
    except Exception as exc:
        print("rs backfill failed:", exc)
        try:
            record_sync("regular_season_gap", count=0, source="post_game_cron", error=str(exc)[:200])
        except Exception:
            pass

    series_refreshed = build_or_refresh_bracket(db, season)
    print("bracket refreshed:", series_refreshed)
    try:
        record_sync("bracket_refresh", count=series_refreshed, source="post_game_cron")
    except Exception:
        pass

    injuries_result = sync_injuries(db, season=season)
    print("sync_injuries:", injuries_result)
    try:
        injury_count = int(injuries_result.get("count", 0)) if isinstance(injuries_result, dict) else 0
        record_sync("injuries", count=injury_count, source="post_game_cron")
    except Exception:
        pass

    print("sync_official_team_general_splits playoff:", sync_official_team_general_splits(db, season=season, is_playoff=True))
    print("sync_official_team_shooting_splits playoff:", sync_official_team_shooting_splits(db, season=season, is_playoff=True))
    try:
        record_sync("team_splits_playoff", count=0, source="post_game_cron")
    except Exception:
        pass
finally:
    db.close()
print(
    "daily_sync_summary: series_refreshed=", series_refreshed,
    "games_refreshed=", games_refreshed,
    "playoff_backfilled=", len(backfilled_ids),
    "rs_backfilled=", len(rs_backfilled_ids),
)
PYEOF
  # Post-game also pulls box scores + Synergy/hustle for the game that just
  # finished so the MVP composite + leaderboards reflect tonight's outcome.
  # --fast skips the slow per-player tracking dashboard pass; that runs in
  # the morning daily sync.
  PYTHONPATH=. "$PYTHON_BIN" scripts/sync_playoff_full.py --fast "$SEASON" >> "$LOG" 2>&1 || true

  # Sprint 78 CF5 — refresh streaks + career milestone snapshots after the
  # game logs settle. Non-fatal: the /milestones page falls back to the
  # last successful snapshot if this hiccups.
  PYTHONPATH=. "$PYTHON_BIN" data/sync_streaks_milestones.py --season "$SEASON" >> "$LOG" 2>&1 || true

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
from services.sync_freshness import record_sync
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    result = sync_injuries(db, season=season)
    print("sync_injuries:", result)
    try:
        count = int((result or {}).get("count", 0)) if isinstance(result, dict) else 0
        record_sync("injuries", count=count, source="daily_sync.sh")
    except Exception:
        pass
finally:
    db.close()
PYEOF

# 3b. Historical injury history seed — Sprint 78 FO5. Idempotent upsert from
# the seeded CSV; rows for unknown player_ids are skipped automatically.
# Runs after the live injuries sync so the duration model always has a
# populated cohort table.
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from data.sync_injury_history import upsert_seed_csv
db = SessionLocal()
try:
    print("sync_injury_history seed:", upsert_seed_csv(db, verbose=False))
finally:
    db.close()
PYEOF

# 3c. Sprint 98 — regular-season gap detector. Mirrors Sprint 97's playoff
# backfill: walks the CDN season schedule, compares to game_logs, and
# inserts any regular-season Final that the warehouse pipeline missed.
# Cheap in steady state: 1 schedule fetch, 0 per-game probes when no gaps.
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1 || true
import os, sys
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.regular_season_gap_detector import detect_and_backfill_regular_season_gaps
from services.sync_freshness import record_sync
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    backfilled = detect_and_backfill_regular_season_gaps(db, season)
    if backfilled:
        print("RS BACKFILL recovered", len(backfilled), "missing games:", backfilled)
    else:
        print("rs backfill: no gaps found")
except Exception as exc:
    print("rs backfill failed:", exc)
    try:
        record_sync("regular_season_gap", count=0, source="daily_sync.sh", error=str(exc)[:200])
    except Exception:
        pass
finally:
    db.close()
PYEOF

# 4. Materialize standings
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1
import sys, os
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.standings_service import materialize_standings
from services.sync_freshness import record_sync
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    result = materialize_standings(season=season, db=db)
    print("materialize_standings:", result)
    try:
        count = int((result or {}).get("count", 0)) if isinstance(result, dict) else 0
        record_sync("standings", count=count, source="daily_sync.sh")
    except Exception:
        pass
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
from services.sync_freshness import record_sync
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    season_stats = sync_official_season_stats(db, season=season)
    print("sync_official_season_stats:", season_stats)
    team_stats = sync_official_team_season_stats(db, season=season)
    print("sync_official_team_season_stats:", team_stats)
    team_general = sync_official_team_general_splits(db, season=season)
    print("sync_official_team_general_splits:", team_general)
    team_shooting = sync_official_team_shooting_splits(db, season=season)
    print("sync_official_team_shooting_splits:", team_shooting)
    try:
        def _count(r):
            return int((r or {}).get("count", 0)) if isinstance(r, dict) else 0
        record_sync("season_stats", count=_count(season_stats), source="daily_sync.sh")
        record_sync("team_season_stats", count=_count(team_stats), source="daily_sync.sh")
        record_sync("team_general_splits", count=_count(team_general), source="daily_sync.sh")
        record_sync("team_shooting_splits", count=_count(team_shooting), source="daily_sync.sh")
    except Exception:
        pass
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
  # Sprint 79 Stream B — playoff PBP events + on/off + lineup derivations.
  # sync_playoff_full above does NOT touch PBP events or PlayerOnOff/LineupStats;
  # this run fills that gap so the Playoff Command Center stops rendering
  # against regular-season fallbacks.
  PYTHONPATH=. "$PYTHON_BIN" data/sync_playoff_pbp.py --season "$SEASON" >> "$LOG" 2>&1 || true
fi

# Sprint 79 Stream A2 — re-materialize role_expansion_observations after
# season_stats sync completes. Powers the opportunity_v2 uplift KNN. Idempotent
# upsert on (player_id, from_season, to_season).
PYTHONPATH=. "$PYTHON_BIN" data/sync_role_expansion.py >> "$LOG" 2>&1 || true

# Sprint 78 CF5 — recompute active streaks + milestone snapshots once the
# canonical season-stats + game-log data is up-to-date. Non-fatal: the
# /milestones page tolerates stale snapshots.
PYTHONPATH=. "$PYTHON_BIN" data/sync_streaks_milestones.py --season "$SEASON" >> "$LOG" 2>&1 || true

# Sprint 81 — Spotrac salary scraper with seed_csv fallback.
# When Spotrac blocks (anti-bot) or any parse error occurs, sync_salary_data
# transparently falls back to data/seed/contracts_2025_26.csv so Trade Machine
# never goes dark. Logs include `fallback_used=true` when the fallback fired.
PYTHONPATH=. "$PYTHON_BIN" data/sync_salaries.py --source spotrac --season "$SEASON" >> "$LOG" 2>&1 || true

# Sprint 81 — ProSportsTransactions injury history scraper. Falls back to
# the synthetic seed CSV on any failure so the Injury Impact panel stays
# functional. PST is not rate-limited aggressively but we run nightly only.
PYTHONPATH=. "$PYTHON_BIN" data/sync_injury_history.py --source prosportstransactions >> "$LOG" 2>&1 || true

# Sprint 81 — Sports Reference college basketball draft prospects scraper.
# Falls back to seed CSV on any failure.
PYTHONPATH=. "$PYTHON_BIN" data/sync_draft_prospects.py --source sportsreference --year 2026 --season "$SEASON" >> "$LOG" 2>&1 || true

# Sprint 81 B2 — materialize Basketball Value + 5-modifier vectors per
# (player, season) referenced by award_voting. Activates mvp_case_v5
# calibrated weights once the cohort is large enough (>= 5 seasons).
PYTHONPATH=. "$PYTHON_BIN" data/materialize_award_modifiers.py >> "$LOG" 2>&1 || true

# Sprint 81 B3 — sync new official data domains (player splits + play types)
# inline as Python so we share a single SessionLocal instead of paying the
# venv startup cost twice.
"$PYTHON_BIN" - <<'PYEOF' >> "$LOG" 2>&1 || true
import os, sys
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.sync_service import (
    sync_official_player_general_splits,
    sync_official_play_type_stats,
)
season = os.environ.get("SEASON", "2024-25")
db = SessionLocal()
try:
    print("sync_official_player_general_splits:", sync_official_player_general_splits(db, season=season))
    print("sync_official_play_type_stats:", sync_official_play_type_stats(db, season=season))
finally:
    db.close()
PYEOF

# Sprint 88 Stream A — daily syncs for hustle (player + team, single API call each)
# and team tracking (12 calls × 0.6s ≈ 7s wall-clock). Player tracking is weekly
# (450 calls = ~5 min) and runs from infra/cron.txt's separate Sunday entry.
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync: hustle + team tracking" >> "$LOG"
"$PYTHON_BIN" - <<PYEOF >> "$LOG" 2>&1
import os, sys
sys.path.insert(0, os.getcwd())
from db.database import SessionLocal
from services.gravity_sync_service import (
    sync_player_hustle_stats,
    sync_team_hustle_stats,
    sync_team_tracking_stats,
)
from services.sync_freshness import record_sync
season = os.environ.get("SEASON", "2024-25")
season_type = "Playoffs" if os.environ.get("IS_PLAYOFFS") == "1" else "Regular Season"
db = SessionLocal()
try:
    player_hustle = sync_player_hustle_stats(db, season=season, season_type=season_type)
    print("sync_player_hustle_stats:", player_hustle)
    team_hustle = sync_team_hustle_stats(db, season=season, season_type=season_type)
    print("sync_team_hustle_stats:", team_hustle)
    team_tracking = sync_team_tracking_stats(db, season=season, season_type=season_type)
    print("sync_team_tracking_stats:", team_tracking)
    try:
        def _count(r):
            return int((r or {}).get("count", 0)) if isinstance(r, dict) else 0
        record_sync("hustle_player", count=_count(player_hustle), source="daily_sync.sh")
        record_sync("hustle_team", count=_count(team_hustle), source="daily_sync.sh")
        record_sync("team_tracking", count=_count(team_tracking), source="daily_sync.sh")
    except Exception:
        pass
finally:
    db.close()
PYEOF

# Sprint 88 Stream C2 — clear expired SQLite cache rows so cache.db doesn't
# grow unboundedly. CacheManager.clear_expired() was defined but never called
# until Sprint 88.
"$PYTHON_BIN" - <<PYEOF >> "$LOG" 2>&1
import os, sys
sys.path.insert(0, os.getcwd())
from data.cache import CacheManager
from services.sync_freshness import record_sync
deleted = CacheManager.clear_expired()
print(f"cache cleanup: {deleted} expired rows deleted from cache.db")
try:
    record_sync("cache_db_cleanup", count=deleted, source="daily_sync.sh")
except Exception:
    pass
PYEOF

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] daily_sync complete season=$SEASON post_game=$POST_GAME_MODE is_playoffs=$IS_PLAYOFFS" >> "$LOG"
