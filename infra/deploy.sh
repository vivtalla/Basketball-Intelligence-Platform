#!/bin/bash
# CourtVue Labs — deploy script. Run after: git pull origin master
# Usage:
#   bash infra/deploy.sh             # update deps + restart services
#   bash infra/deploy.sh --migrate   # also run Alembic migrations
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$REPO_ROOT/backend"
PYTHON="$BACKEND/venv/bin/python"
PIP="$BACKEND/venv/bin/pip"
MIGRATE="${1:-}"

echo "[deploy] Repo: $REPO_ROOT"
echo "[deploy] Updating pip dependencies..."
cd "$BACKEND"
"$PIP" install -q -r requirements.txt

if [ "$MIGRATE" = "--migrate" ]; then
    echo "[deploy] Running Alembic migrations..."
    # /etc/bip/env uses KEY=value (no `export`) so wrap with set -a/+a so the
    # subprocess `alembic` actually inherits DATABASE_URL.
    set -a
    source /etc/bip/env
    set +a
    "$PYTHON" -m alembic upgrade head
    echo "[deploy] Migrations complete."
fi

echo "[deploy] Validating Caddyfile..."
caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

echo "[deploy] Reloading Caddy..."
systemctl reload caddy

echo "[deploy] Restarting bip-api..."
systemctl restart bip-api

echo "[deploy] Waiting for health check..."
sleep 4

# Health check via localhost (direct to uvicorn loopback port)
HTTP_STATUS=$(curl -so /dev/null -w "%{http_code}" --max-time 10 http://127.0.0.1:8000/api/health || echo "000")
if [ "$HTTP_STATUS" = "200" ]; then
    echo "[deploy] Health check PASSED (HTTP $HTTP_STATUS)"
else
    echo "[deploy] Health check FAILED (HTTP $HTTP_STATUS)"
    echo "[deploy] Check logs: journalctl -u bip-api -n 50"
    exit 1
fi

echo "[deploy] Deploy complete."
