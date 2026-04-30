# Database Hosting Runbook

CourtVue Labs production database lives on a Hetzner Cloud CX22 VM
(`postgresql://bip@<vm-ip>:5432/bip`) with nightly `pg_dump` backups to
Cloudflare R2. The local laptop Postgres remains as a development fallback.

This document is the operational source of truth for the DB layer. Update it
whenever the topology, credentials path, or backup strategy changes.

---

## Topology

```
┌─────────────────────┐          ┌──────────────────────────────────┐
│  Vivek's MacBook    │          │  Hetzner CX22 — Falkenstein/Ash  │
│                     │          │  ──────────────────────────────  │
│  - FastAPI (dev)    │ ───TCP──▶│  - Postgres 16 (port 5432)        │
│  - Next.js dev      │          │  - cron: daily_sync.sh             │
│  - Local Postgres   │          │  - cron: bip-backup.sh (R2)        │
│    (dev fallback)   │          │  - logs: /var/log/bip-*.log        │
└─────────────────────┘          └──────────────────────────────────┘
                                              │
                                              ▼  nightly pg_dump | gzip
                                     ┌─────────────────────┐
                                     │  Cloudflare R2      │
                                     │  bip-backups bucket │
                                     │  (10 GB free tier)  │
                                     └─────────────────────┘
```

Cost: ~€4.51/month (Hetzner CX22) + $0 (R2 within free tier) ≈ **$5/month total**.

---

## Connecting

The `DATABASE_URL` env var drives both the FastAPI backend and any sync/CLI
script. Defaults to `postgresql://localhost/bip` so the codebase falls back
to the laptop when the env var is unset.

### Secrets file (laptop)

`~/.bip-env` — `chmod 600`, NEVER committed:
```bash
export DATABASE_URL="postgresql://bip:STRONGPASSWORD@<hetzner-ip>:5432/bip"
```

Source it before any backend / CLI work pointed at production:
```bash
source ~/.bip-env
uvicorn main:app                       # reads DATABASE_URL from env
python data/sync_role_expansion.py     # same
```

### Secrets file (Hetzner VM)

`/etc/bip/env` — owned by `root:root`, `chmod 600`. Loaded by
`bip-backup.sh` and any cron job that needs it.

```bash
PGUSER=bip
PGDATABASE=bip
# PGPASSWORD via ~bip/.pgpass (preferred) or here as a fallback
AWS_ACCESS_KEY_ID=<r2-token-id>
AWS_SECRET_ACCESS_KEY=<r2-token-secret>
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_BUCKET=bip-backups
```

---

## Day-1 Provisioning

### 1. Create the VM
1. Hetzner Cloud → New Project → "courtvue-prod"
2. New Server → CX22, Ubuntu 24.04 LTS, nearest region (Ashburn `ash` for east-coast US, Falkenstein `fsn1` for Europe)
3. Add SSH key, deny password auth
4. Note the assigned public IP

### 2. Configure firewall (Hetzner Cloud Firewall, NOT just `ufw`)
Inbound rules:
- TCP 22 from your laptop's public IP
- TCP 5432 from your laptop's public IP
- ICMP (optional, helps debugging)

**Never `0.0.0.0/0`** for 5432 — you will get scanned within hours.

### 3. Install Postgres + tooling
```bash
ssh ubuntu@<vm-ip>
sudo apt update && sudo apt upgrade -y
sudo apt install -y postgresql-16 postgresql-contrib awscli unattended-upgrades fail2ban logrotate
sudo systemctl enable --now postgresql
```

### 4. Apply Postgres tuning
Append the contents of `infra/postgresql.conf.snippet` to
`/etc/postgresql/16/main/postgresql.conf`, then:
```bash
sudo systemctl restart postgresql
```

### 5. Create the `bip` user + database
```bash
sudo -u postgres psql
postgres=# CREATE USER bip WITH PASSWORD 'STRONGPASSWORD';
postgres=# CREATE DATABASE bip OWNER bip;
postgres=# \q
```

### 6. Configure `pg_hba.conf` for remote auth
Edit `/etc/postgresql/16/main/pg_hba.conf`, add (above the default lines):
```
hostssl  bip  bip  0.0.0.0/0  scram-sha-256
```
(Hetzner firewall already restricts the source IP — `0.0.0.0/0` here just
means "any IP that the firewall allows through".)

```bash
sudo systemctl reload postgresql
```

### 7. Migrate the data
On laptop:
```bash
pg_dump --format=custom --compress=9 bip > /tmp/bip-snapshot.dump
scp /tmp/bip-snapshot.dump ubuntu@<vm-ip>:/tmp/
```

On VM:
```bash
PGPASSWORD=STRONGPASSWORD pg_restore \
  --host=localhost --username=bip --dbname=bip \
  --no-owner --no-acl /tmp/bip-snapshot.dump
```

### 8. Verify the migration
On laptop:
```bash
python infra/verify_migration.py \
  --source postgresql://localhost/bip \
  --target postgresql://bip:STRONGPASSWORD@<vm-ip>:5432/bip \
  --tolerance 0
```
Should print `PASS: N tables, M rows, alembic_version=0017_sprint80_raw_payload_ttl`.

### 9. Smoke-test the backend against the cloud DB
```bash
source ~/.bip-env
cd backend && uvicorn main:app
# in another shell:
curl http://localhost:8000/api/leaderboards/teams?season=2025-26
curl http://localhost:8000/api/trade/contracts/BOS
```

---

## Backups

`pg_dump` runs nightly at 4am UTC from VM cron, streams gzip-compressed
output to Cloudflare R2 via `infra/bip-backup.sh`. Retention via
`infra/bip-backup-prune.sh`: 7 daily + 4 weekly + 3 monthly.

### Restoring from R2 — emergency recovery
```bash
# 1. Pull the dump locally (compressed)
aws --endpoint=$R2_ENDPOINT s3 cp s3://bip-backups/bip-20260501.dump.gz - \
  | gunzip > /tmp/bip-restore.dump

# 2. Restore into a fresh DB
createdb bip_restore
pg_restore --dbname=bip_restore --no-owner --no-acl /tmp/bip-restore.dump

# 3. Sanity-check row counts
python infra/verify_migration.py \
  --source postgresql://localhost/bip \
  --target postgresql://localhost/bip_restore \
  --tolerance 100   # allow drift if prod has diverged

# 4. Promote (rename or update DATABASE_URL)
```

Total time: ~10 minutes for a 1.1 GB compressed dump.

### Restore drill — run quarterly
The `bip-backup-verify.sh` cron runs Sundays at 5am UTC and emails on
failure. Once a quarter, manually verify: ssh to VM, run the script, check
log output. If verification has been failing silently, the cron's MAILTO
should have flagged it — but trust-but-verify.

---

## Common Operations

### Connect via psql
```bash
source ~/.bip-env
psql "$DATABASE_URL"
```

### Run an Alembic migration against production
```bash
source ~/.bip-env
cd backend && python -m alembic upgrade head
```

### Trigger a manual sync from VM
```bash
ssh ubuntu@<vm-ip>
cd /home/ubuntu/bip/backend
bash data/daily_sync.sh                   # full daily run
bash data/daily_sync.sh --post-game       # cheap refresh
bash data/daily_sync.sh --dry-run         # what would it do
```

### Inspect cron logs
```bash
ssh ubuntu@<vm-ip>
tail -f /var/log/bip-sync.log              # daily / post-game sync
tail -f /var/log/bip-backup.log            # backups
crontab -l                                  # see active schedule
```

### Take an ad-hoc backup before risky migration
```bash
ssh ubuntu@<vm-ip>
/home/ubuntu/bip/infra/bip-backup.sh
# upload key will be bip-YYYYMMDD.dump.gz; rename in R2 if you want it pinned
```

---

## Troubleshooting

### "could not connect to server" from laptop
1. Verify Hetzner Cloud Firewall has your current public IP. ISPs rotate.
2. Check `sudo systemctl status postgresql` on VM.
3. `tail /var/log/postgresql/postgresql-16-main.log` on VM for connection errors.

### Slow queries from laptop
1. Run the query against a local DB copy — if fast there, it's network latency.
2. Pick a closer Hetzner region (Ashburn for US east, Falkenstein for Europe).
3. Worst case: keep local Postgres as primary dev DB, set up logical replication
   from cloud (Sprint 81 candidate).

### Backup cron failed — MAILTO didn't fire
Hetzner blocks port 25 for new accounts. Either:
- Use SendGrid free tier (100 emails/day) via `ssmtp` on the VM, OR
- Switch cron MAILTO target to a Pushover / Slack webhook via a wrapper script

### Hetzner instance hardware failure (rare but happens)
1. Restore from R2 onto a new CX22 (10-15 min): see "Restoring from R2" above
2. Update `~/.bip-env` on laptop with new IP
3. Update `crontab` on new VM
4. Re-run latest sync to pull any data ingested between last backup and failure

### Account suspension / billing failure
Set up Hetzner account alerts. Pay annually if budget allows (slight discount).
R2 backups in a separate Cloudflare account = independent recovery path.

---

## Future Migrations

When DB grows past 30 GB or query volume increases:
- **Postgres 17 upgrade**: in-place via `pg_upgrade` on VM, ~30 min downtime
- **Larger VM**: Hetzner CX32 (4 vCPU / 8 GB / 80 GB) at ~€8/month — `hetzner upgrade` is one click
- **Read replica**: spin up a second CX22, set up streaming replication
- **Managed Postgres** (Neon Launch / DigitalOcean): if ops becomes painful

The existing `DATABASE_URL` env-var pattern means any of these is a config swap, not a code change.
