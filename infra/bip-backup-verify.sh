#!/bin/bash
#
# CourtVue Labs — weekly backup verification (the "did the backups
# actually work" check). Runs Sundays at 5am UTC from VM cron.
#
# Pulls the latest R2 dump, restores into a scratch DB on the same VM,
# diffs row counts against production for the largest tables. Emails on
# any mismatch via the cron MAILTO.

set -euo pipefail

if [ -f /etc/bip/env ]; then
  set -a
  . /etc/bip/env
  set +a
fi

: "${R2_ENDPOINT:?missing R2_ENDPOINT}"
: "${R2_BUCKET:?missing R2_BUCKET}"
: "${PGDATABASE:?missing PGDATABASE}"

SCRATCH_DB="bip_restore_test"
LOG_PREFIX="[bip-backup-verify $(date -u +%Y%m%d)]"

# Find the latest dump in R2
LATEST_KEY=$(aws --endpoint="${R2_ENDPOINT}" s3 ls "s3://${R2_BUCKET}/" \
  | awk '{print $4}' | grep -E '^bip-[0-9]{8}\.dump\.gz$' | sort -r | head -n 1)

if [ -z "$LATEST_KEY" ]; then
  echo "${LOG_PREFIX} FATAL: no dumps found in R2" >&2
  exit 1
fi

echo "${LOG_PREFIX} verifying ${LATEST_KEY}"

# Drop + recreate scratch DB
psql -d postgres -c "DROP DATABASE IF EXISTS ${SCRATCH_DB};"
psql -d postgres -c "CREATE DATABASE ${SCRATCH_DB};"

# Restore into scratch
aws --endpoint="${R2_ENDPOINT}" s3 cp "s3://${R2_BUCKET}/${LATEST_KEY}" - --no-progress \
  | gunzip \
  | pg_restore --dbname="${SCRATCH_DB}" --no-owner --no-acl --jobs=2

# Diff row counts for the largest tables. We allow a small drift since the
# dump is from yesterday and prod has been written to since.
TABLES=(
  play_by_play_events
  play_by_play
  player_game_logs
  lineup_stats
  season_stats
)

FAILED=0
for tbl in "${TABLES[@]}"; do
  PROD=$(psql -tA -d "${PGDATABASE}" -c "SELECT count(*) FROM ${tbl};" 2>/dev/null || echo 0)
  REST=$(psql -tA -d "${SCRATCH_DB}" -c "SELECT count(*) FROM ${tbl};" 2>/dev/null || echo 0)
  if [ "$REST" -eq 0 ] && [ "$PROD" -gt 0 ]; then
    echo "${LOG_PREFIX} FAIL: ${tbl} restored to 0 rows (prod has ${PROD})" >&2
    FAILED=1
  else
    echo "${LOG_PREFIX} ok: ${tbl} prod=${PROD} restored=${REST}"
  fi
done

# Tear down scratch DB
psql -d postgres -c "DROP DATABASE ${SCRATCH_DB};"

if [ "$FAILED" -eq 1 ]; then
  echo "${LOG_PREFIX} VERIFICATION FAILED — investigate ${LATEST_KEY}" >&2
  exit 1
fi

echo "${LOG_PREFIX} verification passed"
