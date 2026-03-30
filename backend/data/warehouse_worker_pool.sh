#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SEASON="${1:-${WAREHOUSE_SEASON:-2024-25}}"
WORKER_COUNT="${WAREHOUSE_WORKER_COUNT:-3}"
MAX_JOBS="${WAREHOUSE_MAX_JOBS:-5000}"
IDLE_SLEEP="${WAREHOUSE_IDLE_SLEEP:-15}"
SUMMARY_EVERY="${WAREHOUSE_SUMMARY_EVERY:-25}"
LOG_DIR="${WAREHOUSE_LOG_DIR:-$BACKEND_DIR/logs/warehouse}"
PID_DIR="${WAREHOUSE_PID_DIR:-$BACKEND_DIR/tmp/warehouse-pids}"
PYTHON_BIN="${WAREHOUSE_PYTHON_BIN:-$BACKEND_DIR/venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

mkdir -p "$LOG_DIR" "$PID_DIR"

echo "Starting $WORKER_COUNT warehouse workers for season $SEASON"

for worker_id in $(seq 1 "$WORKER_COUNT"); do
  pid_file="$PID_DIR/${SEASON}-worker-${worker_id}.pid"
  log_file="$LOG_DIR/${SEASON}-worker-${worker_id}.log"

  if [ -f "$pid_file" ]; then
    existing_pid="$(cat "$pid_file")"
    if kill -0 "$existing_pid" 2>/dev/null; then
      echo "Worker $worker_id already running with PID $existing_pid"
      continue
    fi
  fi

  (
    cd "$BACKEND_DIR"
    nohup "$PYTHON_BIN" data/warehouse_jobs.py \
      --season "$SEASON" \
      --max-jobs "$MAX_JOBS" \
      --loop \
      --idle-sleep "$IDLE_SLEEP" \
      --summary-every "$SUMMARY_EVERY" \
      >> "$log_file" 2>&1 &
    echo $! > "$pid_file"
  )

  echo "Worker $worker_id started: pid $(cat "$pid_file"), log $log_file"
done
