#!/bin/bash
#
# CourtVue Labs — nightly Postgres backup to Cloudflare R2.
#
# Runs from VM cron at 4am UTC daily. Streams pg_dump output through gzip
# directly to R2 via aws-cli to avoid landing the whole 200+ MB dump on
# local disk.
#
# Required environment (sourced from /etc/bip/env):
#   AWS_ACCESS_KEY_ID       — R2 API token ID
#   AWS_SECRET_ACCESS_KEY   — R2 API token secret
#   R2_ENDPOINT             — https://<account-id>.r2.cloudflarestorage.com
#   R2_BUCKET               — typically "bip-backups"
#   PGUSER, PGDATABASE      — Postgres connection (PGPASSWORD via .pgpass)
#
# Restore an arbitrary dump:
#   aws --endpoint=$R2_ENDPOINT s3 cp s3://$R2_BUCKET/bip-20260501.dump.gz - \
#     | gunzip | pg_restore --dbname=bip_test --no-owner --no-acl

set -euo pipefail

# Source secrets — never inline credentials in this script
if [ -f /etc/bip/env ]; then
  set -a
  . /etc/bip/env
  set +a
else
  echo "[bip-backup] FATAL: /etc/bip/env missing" >&2
  exit 1
fi

# Required vars guard
: "${R2_ENDPOINT:?missing R2_ENDPOINT}"
: "${R2_BUCKET:?missing R2_BUCKET}"
: "${PGDATABASE:?missing PGDATABASE}"

DATE=$(date -u +%Y%m%d)
DUMP_KEY="bip-${DATE}.dump.gz"
LOG_PREFIX="[bip-backup ${DATE}]"

echo "${LOG_PREFIX} starting"

# Stream pg_dump → gzip → R2. -Fc is custom format, -Z0 because we gzip
# externally for transparent .gz that R2 can serve as-is. -j 1 means single
# job (CX22 has 2 vCPU; parallel dump complicates streaming).
pg_dump -Fc -Z0 "${PGDATABASE}" \
  | gzip -9 \
  | aws --endpoint="${R2_ENDPOINT}" s3 cp - "s3://${R2_BUCKET}/${DUMP_KEY}" \
       --no-progress

echo "${LOG_PREFIX} uploaded ${DUMP_KEY}"

# Run retention cleanup (7 daily / 4 weekly / 3 monthly)
exec /home/ubuntu/bip/infra/bip-backup-prune.sh
