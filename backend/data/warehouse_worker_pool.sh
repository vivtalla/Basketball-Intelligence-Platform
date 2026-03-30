#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ "${1:-}" = "start" ] || [ "${1:-}" = "stop" ] || [ "${1:-}" = "restart" ] || [ "${1:-}" = "status" ]; then
  ACTION="$1"
  SEASON="${2:-${WAREHOUSE_SEASON:-2024-25}}"
else
  ACTION="${WAREHOUSE_POOL_ACTION:-start}"
  SEASON="${1:-${WAREHOUSE_SEASON:-2024-25}}"
fi
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

stop_worker() {
  local worker_id="$1"
  local pid_file="$PID_DIR/${SEASON}-worker-${worker_id}.pid"

  if [ ! -f "$pid_file" ]; then
    echo "Worker $worker_id is not running"
    return
  fi

  local existing_pid
  existing_pid="$(cat "$pid_file")"
  if kill -0 "$existing_pid" 2>/dev/null; then
    kill "$existing_pid"
    echo "Stopped worker $worker_id (PID $existing_pid)"
  else
    echo "Worker $worker_id PID file was stale"
  fi
  rm -f "$pid_file"
}

if [ "$ACTION" = "stop" ] || [ "$ACTION" = "restart" ]; then
  echo "Stopping warehouse workers for season $SEASON"
  for worker_id in $(seq 1 "$WORKER_COUNT"); do
    stop_worker "$worker_id"
  done
fi

if [ "$ACTION" = "stop" ]; then
  exit 0
fi

if [ "$ACTION" = "status" ]; then
  for worker_id in $(seq 1 "$WORKER_COUNT"); do
    pid_file="$PID_DIR/${SEASON}-worker-${worker_id}.pid"
    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      echo "Worker $worker_id running with PID $(cat "$pid_file")"
    else
      echo "Worker $worker_id stopped"
    fi
  done
  exit 0
fi

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
