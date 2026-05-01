#!/bin/bash
# CourtVue Labs — one-time Caddy install and bip-api service setup.
# Run as: sudo bash infra/caddy-install.sh
# Run from: /home/ubuntu/bip (after git pull)
set -euo pipefail

echo "[caddy-install] Installing Caddy from official repo..."
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
    | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
    | tee /etc/apt/sources.list.d/caddy-stable.list
apt update && apt install -y caddy

echo "[caddy-install] Installing Caddyfile..."
cp /home/ubuntu/bip/infra/Caddyfile /etc/caddy/Caddyfile
mkdir -p /var/log/caddy
chown caddy:caddy /var/log/caddy

echo "[caddy-install] Installing bip-api systemd service..."
cp /home/ubuntu/bip/infra/bip-api.service /etc/systemd/system/bip-api.service
systemctl daemon-reload
systemctl enable bip-api

echo "[caddy-install] Enabling Caddy..."
systemctl enable caddy

echo ""
echo "=== Next steps ==="
echo "1. Install pip deps:  cd /home/ubuntu/bip/backend && ./venv/bin/pip install gunicorn==23.0.0"
echo "2. Add to /etc/bip/env:"
echo "     NBA_API_USER_FETCH_DISABLED=true"
echo "     CORS_ORIGINS=https://courtvue.app,https://www.courtvue.app"
echo "3. Run migrations:  source /etc/bip/env && ./venv/bin/python -m alembic upgrade head"
echo "4. Start services:  systemctl start bip-api && systemctl reload caddy"
echo "5. Watch cert:      journalctl -u caddy -f  (Ctrl+C once cert obtained)"
echo "6. Test:            curl -sf https://api.courtvue.app/api/health"
echo ""
echo "[caddy-install] Public mode — no password required."
echo "[caddy-install] Make sure api.courtvue.app is orange-cloud (proxied) at Cloudflare."
