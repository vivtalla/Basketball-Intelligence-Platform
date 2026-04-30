#!/bin/bash
#
# CourtVue Labs — R2 backup retention.
#
# Keeps:
#   - last 7 daily dumps
#   - last 4 Sunday dumps (weekly snapshots)
#   - last 3 dumps from the 1st of the month (monthly snapshots)
#
# Total retention: ~14 dumps × ~200 MB compressed ≈ 2.8 GB (well under
# Cloudflare R2 free tier of 10 GB).
#
# Runs as the tail of bip-backup.sh — same secrets/env requirements.

set -euo pipefail

if [ -f /etc/bip/env ]; then
  set -a
  . /etc/bip/env
  set +a
fi

: "${R2_ENDPOINT:?missing R2_ENDPOINT}"
: "${R2_BUCKET:?missing R2_BUCKET}"

LOG_PREFIX="[bip-backup-prune $(date -u +%Y%m%d)]"

# List all dumps, parse the YYYYMMDD from the key, sort descending
ALL_KEYS=$(aws --endpoint="${R2_ENDPOINT}" s3 ls "s3://${R2_BUCKET}/" \
  | awk '{print $4}' | grep -E '^bip-[0-9]{8}\.dump\.gz$' | sort -r)

if [ -z "$ALL_KEYS" ]; then
  echo "${LOG_PREFIX} no existing dumps found"
  exit 0
fi

# Build the keep-set
KEEP=""

# Last 7 dumps regardless of date
KEEP="${KEEP}$(echo "$ALL_KEYS" | head -n 7)
"

# Last 4 Sundays
for key in $ALL_KEYS; do
  date_str=$(echo "$key" | sed -E 's/bip-([0-9]{8})\.dump\.gz/\1/')
  dow=$(date -u -d "${date_str:0:4}-${date_str:4:2}-${date_str:6:2}" +%u 2>/dev/null || echo "")
  if [ "$dow" = "7" ]; then  # Sunday
    KEEP="${KEEP}${key}
"
    sundays=$((${sundays:-0} + 1))
    [ "$sundays" -ge 4 ] && break
  fi
done

# Last 3 first-of-month
months=0
for key in $ALL_KEYS; do
  date_str=$(echo "$key" | sed -E 's/bip-([0-9]{8})\.dump\.gz/\1/')
  if [ "${date_str:6:2}" = "01" ]; then
    KEEP="${KEEP}${key}
"
    months=$((months + 1))
    [ "$months" -ge 3 ] && break
  fi
done

# Dedupe keep-set
KEEP=$(echo "$KEEP" | sort -u | grep -v '^$' || true)

# Anything not in KEEP gets deleted
for key in $ALL_KEYS; do
  if ! echo "$KEEP" | grep -qx "$key"; then
    aws --endpoint="${R2_ENDPOINT}" s3 rm "s3://${R2_BUCKET}/${key}" --no-progress
    echo "${LOG_PREFIX} pruned ${key}"
  fi
done

echo "${LOG_PREFIX} retention complete"
