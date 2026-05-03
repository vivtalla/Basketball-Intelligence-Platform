# CourtVue Labs — Deployment Runbook

## Infrastructure

| Component | Location | Notes |
|-----------|----------|-------|
| PostgreSQL 16 | Hetzner CX22 (`5.78.114.15`) | Running, migrated Sprint 80 |
| FastAPI backend | Hetzner CX22 | Served by gunicorn + Caddy |
| Next.js frontend | Vercel | Auto-deploys from GitHub `master` |
| DNS / CDN / WAF | Cloudflare | `courtvue.app`, orange-cloud for both API and frontend |

**Public access:** Sprint 82d switched the platform to fully public read-only. There is no login. Cloudflare WAF rate-limits abuse; FastAPI itself runs with `NBA_API_USER_FETCH_DISABLED=true` so user requests can never trigger live calls to `stats.nba.com` (cron continues to fetch normally).

## First-Time Setup (VM)

### Prerequisites
1. Hetzner Cloud Firewall: open TCP 80 and 443 from `0.0.0.0/0` (keep 5432 locked to laptop IP only)
2. SSH access: add your `~/.ssh/id_ed25519.pub` to `/home/ubuntu/.ssh/authorized_keys` via Hetzner VNC console
3. Domain `courtvue.app` registered at Cloudflare Registrar with DNS pointing to the VM (see Cloudflare DNS section)

### Install Caddy + bip-api service
```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip && git pull origin master
sudo bash infra/caddy-install.sh
```

### Install gunicorn + run pending migrations
```bash
cd /home/ubuntu/bip/backend
./venv/bin/pip install gunicorn==23.0.0
source /etc/bip/env && ./venv/bin/python -m alembic upgrade head
sudo -u postgres psql -d bip -c "VACUUM FULL;"   # reclaim space from Sprint 81 play_by_play drop
```

### Configure environment for public mode
Edit `/etc/bip/env` and add these lines:
```
NBA_API_USER_FETCH_DISABLED=true
CORS_ORIGINS=https://courtvue.app,https://www.courtvue.app
```

`NBA_API_USER_FETCH_DISABLED=true` ensures user requests never trigger live NBA API calls. Cron jobs in `daily_sync.sh` explicitly override this to `false` so nightly fetches keep working.

### Start services
```bash
sudo systemctl start bip-api
sudo systemctl reload caddy
sudo journalctl -u caddy -f    # watch for "certificate obtained successfully"
# (Ctrl+C once cert is issued; takes ~10s with Cloudflare orange-cloud DNS)
curl -sf https://api.courtvue.app/api/health
# Should return 200 — no credentials needed in public mode
```

### Install Playwright (for PST scraper)
```bash
sudo bash infra/playwright-install.sh
```

## Vercel Setup (Frontend)

1. `vercel.com/new` → Import the GitHub repo
2. Root Directory: `frontend` (CRITICAL — not the repo root)
3. Framework Preset: Next.js (auto-detected)
4. Environment Variables: `NEXT_PUBLIC_API_URL=https://api.courtvue.app`
5. Click Deploy. After build, note the `*.vercel.app` preview URL.

After Vercel issues a preview URL, you may want to add it to `CORS_ORIGINS` on the VM if you ever test against the preview directly:
```bash
sudo nano /etc/bip/env
# CORS_ORIGINS=https://courtvue.app,https://www.courtvue.app,https://<preview>.vercel.app
sudo systemctl restart bip-api
```
The custom domain (`courtvue.app`) is the primary entry point; the Vercel preview URL is mostly for debugging.

## Cloudflare DNS + WAF

Register `courtvue.app` at Cloudflare Registrar (~$12/yr).

### DNS records (Cloudflare → DNS → Records)

| Type | Name | Target | Proxy status |
|------|------|--------|--------------|
| A | `api` | `5.78.114.15` | **Proxied (orange cloud)** — public mode |
| CNAME | `@` (root) | `cname.vercel-dns.com` | Proxied (orange) |
| CNAME | `www` | `cname.vercel-dns.com` | Proxied (orange) |

**Why orange-cloud `api.courtvue.app`:** in public mode, Cloudflare's free WAF rate-limits abuse and hides the origin IP from DDoS scanning. Caddy still terminates TLS at the origin (Cloudflare uses "Full" mode); Caddy reads the real client IP from `CF-Connecting-IP` per the Caddyfile config.

Add `courtvue.app` and `www.courtvue.app` as custom domains in your Vercel project settings.

### Cloudflare WAF rules (free tier — 5 custom rules + 1 rate limit)

In Cloudflare dashboard → Security → WAF → Custom rules:

1. **Block obvious scrapers:**
   - When `(http.user_agent contains "zgrab") or (http.user_agent contains "masscan") or (http.user_agent eq "")`
   - Action: Block

2. **Cloudflare → Security → WAF → Rate limiting rules:**
   - Path: `*api.courtvue.app/*`
   - Threshold: 100 requests per 10 minutes per IP
   - Action: Managed Challenge (CAPTCHA)
   - This is your primary abuse defense for the public API.

### Cache rules (Cloudflare → Caching → Cache Rules)

The daily cron refreshes data overnight. Cache TTLs aligned with that cadence. Free tier allows 5 cache rules.

| Rule | Pattern (priority order) | Cache TTL | Why |
|------|-------------------------|-----------|-----|
| 1 | `hostname=api.courtvue.app AND URI starts_with /api/playoffs/` | 2 hours | Playoff series + bracket + per-series player logs (Sprint 85 B). Refreshes post-game. |
| 2 | `hostname=api.courtvue.app AND URI starts_with /api/standings` | 2 hours | Refreshed post-game |
| 3 | `hostname=api.courtvue.app AND URI starts_with /api/leaderboards` | 6 hours | Updated nightly |
| 4 | `hostname=api.courtvue.app AND URI matches "^/api/(players\|teams)/.*/(splits\|play-types\|tracking\|hustle)$"` | 12 hours | Daily-synced player + team stat dashboards (Sprint 81 splits/play-types + Sprint 85/86 tracking + hustle). Sprint 86 broadened from `/api/players/*/splits` to cover the new endpoints. |
| 5 | `hostname=api.courtvue.app` (catch-all) | 2 hours | Default for `/api/health`, search, anything not matched above. Health bypass is unnecessary because requests are cheap and the catch-all TTL is short. |

Cloudflare's edge cache is what protects the VM from a sudden traffic spike. Without it, a viral moment would fall straight through to the 2-worker gunicorn.

**When to update rule 4:** any new endpoint family that follows the daily-sync cadence (e.g. future shooting splits, advanced stats by player or team) should be added to the regex inside the existing rule rather than creating a new rule (free tier is at the 5-rule cap).

### Backup retention (Sprint 87 — recommended next Cloudflare touch)

`bip-backup-prune.sh` enforces 7 daily / 4 weekly / 3 monthly retention via shell logic. As a second-layer safety net (in case the prune script silently fails), add an R2 lifecycle rule auto-deleting objects older than 90 days:

- Cloudflare dashboard → R2 → bucket settings → Object lifecycle rules → Add rule
- Apply to: all objects in the bucket
- Delete after: 90 days
- OR via API once the AWS CLI is configured: `aws --endpoint=$R2_ENDPOINT s3api put-bucket-lifecycle-configuration --bucket=$R2_BUCKET --lifecycle-configuration file://r2-lifecycle.json`

Audit-flagged but deferred from Sprint 87 because it's a Cloudflare UI step (different domain per the Deferral Policy).

## One-time logrotate install (Sprint 87)

The `bip-api.service` writes gunicorn access logs to `/var/log/bip-api/access.log` (Sprint 87 changed from journal-only). Install the rotation config once per VM:

```bash
sudo cp /home/ubuntu/bip/infra/bip-api.logrotate /etc/logrotate.d/bip-api
sudo logrotate -d /etc/logrotate.d/bip-api   # dry-run validate
```

Logrotate runs daily via Ubuntu's `/etc/cron.daily/logrotate`. Default config: 14-day retention, compressed, copytruncate (no need to signal gunicorn). Verify after first day with `ls -la /var/log/bip-api/`.

## Routine Deploys (after each git push to master)

```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip && git pull origin master
sudo bash infra/deploy.sh            # update + restart
# or with migrations:
sudo bash infra/deploy.sh --migrate
```

## Rollback

```bash
sudo systemctl stop bip-api caddy
# Nothing deleted. Laptop can still connect to Hetzner DB via ~/.bip-env.
sudo systemctl start bip-api caddy  # re-enable anytime
```

## Observability

- Caddy access logs: `/var/log/caddy/bip-api.log` (JSON, includes real client IP via `CF-Connecting-IP`)
- systemd logs: `sudo journalctl -u bip-api -n 100`
- Health endpoint: `https://api.courtvue.app/api/health` (always returns 200 if alive)
- UptimeRobot (free): add an HTTP monitor on `/api/health`, 5-min interval, alert to vivtalla@gmail.com
- Cloudflare Analytics: dashboard → Analytics → Traffic — shows request volume, cache hit ratio, WAF blocks

## Cost summary

| Item | Cost |
|------|------|
| Hetzner CX22 VM | $4.59/mo |
| Cloudflare DNS + CDN + WAF | Free |
| Cloudflare R2 backups | Free tier (well under 10 GB) |
| Cloudflare Registrar (domain) | ~$11.59/yr |
| Vercel (Next.js frontend) | Free hobby tier |
| **Total** | **~$5/mo + $1/mo amortized domain** |
