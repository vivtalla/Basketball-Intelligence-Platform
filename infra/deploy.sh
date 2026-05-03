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
    # subprocess inherits DATABASE_URL.
    set -a
    source /etc/bip/env
    set +a
    # Invoke via `db.migrations` (not raw `alembic`) so the DATABASE_URL env
    # var is honored — alembic.ini hardcodes a passwordless localhost URL
    # which fails against production Postgres.
    "$PYTHON" -m db.migrations
    echo "[deploy] Migrations complete."
fi

# Sprint 88 (E) — auto-sync infra config files into their installed locations.
# Without this, changes to bip-api.service or Caddyfile in the repo silently
# don't take effect because the service unit / Caddy config in /etc/* are
# only seeded once by caddy-install.sh. Sprint 87 surfaced this gap.
sync_if_different() {
    local src="$1"
    local dst="$2"
    local label="$3"
    if [ -f "$src" ] && ! cmp -s "$src" "$dst"; then
        echo "[deploy] Syncing $label: $src → $dst"
        install -m 0644 "$src" "$dst"
        return 0
    fi
    return 1
}

NEED_DAEMON_RELOAD=0
if sync_if_different "$REPO_ROOT/infra/bip-api.service" "/etc/systemd/system/bip-api.service" "bip-api.service"; then
    NEED_DAEMON_RELOAD=1
fi
sync_if_different "$REPO_ROOT/infra/Caddyfile" "/etc/caddy/Caddyfile" "Caddyfile" || true

if [ "$NEED_DAEMON_RELOAD" = "1" ]; then
    echo "[deploy] systemctl daemon-reload (service unit changed)"
    systemctl daemon-reload
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
