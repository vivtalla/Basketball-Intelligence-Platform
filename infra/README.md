# CourtVue Labs — Deployment Runbook

## Infrastructure

| Component | Location | Notes |
|-----------|----------|-------|
| PostgreSQL 16 | Hetzner CX22 (`5.78.114.15`) | Running, migrated Sprint 80 |
| FastAPI backend | Hetzner CX22 | Served by gunicorn + Caddy |
| Next.js frontend | Vercel | Auto-deploys from GitHub `master` |
| DNS / CDN | Cloudflare | `courtvue.app` |

## First-Time Setup (VM)

### Prerequisites
1. Hetzner Cloud Firewall: open TCP 80 and 443 from `0.0.0.0/0` (keep 5432 locked)
2. SSH access: add `~/.ssh/id_ed25519.pub` to `/home/ubuntu/.ssh/authorized_keys` via Hetzner VNC console

### Install Caddy + bip-api service
```
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip && git pull origin master
sudo bash infra/caddy-install.sh
```

### Set the FO password
```
caddy hash-password --plaintext 'YOUR_FO_PASSWORD'
sudo nano /etc/caddy/Caddyfile   # replace <BCRYPT_HASH_PLACEHOLDER>
```

### Install gunicorn + run Sprint 81 migrations
```
cd /home/ubuntu/bip/backend
./venv/bin/pip install gunicorn==23.0.0
source /etc/bip/env && ./venv/bin/python -m alembic upgrade head
```

### Start services
```
sudo systemctl start bip-api
sudo systemctl reload caddy
curl -sf -u courtvue:YOUR_FO_PASSWORD https://api.courtvue.app/api/health
```

### Install Playwright (for PST scraper)
```
sudo bash infra/playwright-install.sh
```

## Vercel Setup (Frontend)

1. `vercel.com/new` → Import GitHub repo → Root Directory: `frontend`
2. Env var: `NEXT_PUBLIC_API_URL=https://api.courtvue.app`
3. Note the `*.vercel.app` preview URL

## CORS Update (after Vercel deploy)

Add to `/etc/bip/env` on VM:
```
CORS_ORIGINS=https://courtvue.app,https://www.courtvue.app,https://<preview>.vercel.app
```
Then: `sudo systemctl restart bip-api`

## Cloudflare DNS

Register `courtvue.app` at Cloudflare Registrar (~$12/yr). DNS records:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| A | `api` | `5.78.114.15` | DNS-only (grey) — Caddy owns TLS |
| CNAME | `@` | `cname.vercel-dns.com` | Proxied (orange) |
| CNAME | `www` | `cname.vercel-dns.com` | Proxied (orange) |

Add `courtvue.app` and `www.courtvue.app` as custom domains in Vercel project settings.

## Routine Deploys (after each git push to master)

```
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip && git pull origin master
sudo bash infra/deploy.sh            # update + restart
# or with migrations:
sudo bash infra/deploy.sh --migrate
```

## Rollback

```
sudo systemctl stop bip-api caddy
# Nothing deleted. Laptop can still connect to Hetzner DB via ~/.bip-env.
sudo systemctl start bip-api caddy  # re-enable anytime
```

## Observability

- Caddy access logs: `/var/log/caddy/bip-api.log`
- systemd logs: `journalctl -u bip-api -n 100`
- Health endpoint: `https://api.courtvue.app/api/health` (bypasses basicauth)
- UptimeRobot: monitor `/api/health` every 5 min, alert to vivtalla@gmail.com
