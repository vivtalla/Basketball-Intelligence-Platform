# Sprint 80 Closeout — Cloud Migration: DB + Cron Off the Laptop

**Completed:** 2026-04-30
**Type:** Single-stream infrastructure sprint
**Cost outcome:** ~$5/month (Hetzner CX22 €4.51 + Cloudflare R2 $0)

---

## What Shipped

### Stream A — Database Migration to Hetzner

**A1. VM provisioning + Postgres install**
- Hetzner CX22 (2 vCPU / 4 GB RAM / 40 GB NVMe SSD, Ashburn VA): `5.78.114.15`
- Ubuntu 24.04 LTS, SSH key auth only, fail2ban installed
- Postgres 16.13 installed and enabled
- `infra/postgresql.conf.snippet` applied: `shared_buffers=1GB`, `effective_cache_size=3GB`, `work_mem=16MB`, `maintenance_work_mem=256MB`, `random_page_cost=1.1`, `max_connections=30`, `password_encryption=scram-sha-256`
- `pg_hba.conf` configured: `hostssl bip bip 0.0.0.0/0 scram-sha-256`
- Hetzner Cloud Firewall applied: TCP 22 + 5432 locked to laptop IP `97.115.178.47/32`

**A2. Pre-flight DB cleanup**
- Alembic migration `0017_sprint80_raw_payload_ttl`: deleted `raw_game_payloads` rows older than 30 days (4,706 rows), freed 184 MB (193 MB → 9 MB)
- `VACUUM FULL raw_game_payloads` run post-delete
- Legacy `play_by_play` table drop deferred — 11+ active service readers found via grep. Deferred to Sprint 81.
- Post-cleanup DB size: ~1.84 GB (from 2.02 GB)

**A3. Migration cutover**
- `pg_dump --format=custom --compress=9 bip` → 123 MB compressed dump
- `scp` to VM + `pg_restore` (completed in ~11 seconds transfer)
- Verification: **PASS: 50 tables, 4,558,469 rows, alembic_version=0017_sprint80_raw_payload_ttl**
- All 14 size mismatches were expected (fresh restore = no bloat vs laptop's live DB)
- `~/.bip-env` on laptop updated: `DATABASE_URL=postgresql://bip:…@5.78.114.15:5432/bip`
- Backend smoke test: `/api/leaderboards/teams`, `/api/trade/contracts/BOS`, `/api/playoffs/today` — all 200 OK

**A4. Backup automation to R2**
- Cloudflare R2 bucket `bip-backups` + API tokens configured
- `infra/bip-backup.sh`: streams `pg_dump -Fc -Z0 | gzip -9 | aws s3 cp -` to R2
- `infra/bip-backup-prune.sh`: 7 daily + 4 weekly + 3 monthly retention
- `infra/bip-backup-verify.sh`: weekly restore drill to `bip_restore_test`, row-count diff, emails on failure
- Manual backup triggered and confirmed: `bip-20260430.dump.gz` (140 MB) in R2 bucket

### Stream B — Cron Migration to Hetzner VM

**B1. Repo + Python environment on VM**
- Repo cloned to `/home/ubuntu/bip` from `https://github.com/vivtalla/CourtVue-Labs.git`
- Python 3.12 venv at `/home/ubuntu/bip/backend/venv` with all requirements installed
- VM smoke test: `players: 1110`, `season_stats: 6486`, `alembic_version: 0017_sprint80_raw_payload_ttl`

**B2. Cron migration**
- `/etc/bip/env` on VM: `DATABASE_URL`, `PGPASSWORD`, R2 credentials (chmod 600)
- Crontab installed (sources `/etc/bip/env` before each job):
  - `0 4 * * *` — `bip-backup.sh` → R2
  - `0 6 * * *` — `daily_sync.sh` (full pipeline)
  - `*/30 * * * *` — `daily_sync.sh --post-game` (playoff gate)
  - `0 5 * * 0` — `bip-backup-verify.sh` (Sunday restore drill)
- Logrotate: `/etc/logrotate.d/bip-sync` — daily rotation, 14-day retention
- `infra/cron.txt` committed and deployed to `/home/ubuntu/bip/infra/cron.txt`

### Salary Data Closeout (Sprint 79 carry-over)

- `contracts_2025_26.csv` expanded: 514 players, 24 known-exact + 490 estimated
- `salary_source` field wired end-to-end: ORM → router → Pydantic model → TypeScript interface → UI
- Trade Machine: amber `est.` badge per player + panel banner when any estimated contracts present

---

## Files Affected

### New
| File | Purpose |
|------|---------|
| `infra/bip-backup.sh` | VM nightly pg_dump → gzip → R2 |
| `infra/bip-backup-prune.sh` | R2 retention cleanup |
| `infra/bip-backup-verify.sh` | Weekly restore drill |
| `infra/bip-backup-verify.sh` | Weekly restore drill |
| `infra/postgresql.conf.snippet` | Committed Postgres tuning for CX22 |
| `infra/cron.txt` | Committed crontab (deployed via `crontab infra/cron.txt`) |
| `infra/verify_migration.py` | Row-count + size diff between two DATABASE_URLs |
| `specs/db-hosting.md` | Operational runbook: VM access, secrets, backup/restore, ops |
| `specs/data-architecture.md` | Updated with full topology diagram + new tables |
| `backend/alembic/versions/0017_sprint80_raw_payload_ttl.py` | TTL raw_game_payloads >30 days |

### Modified
| File | Change |
|------|--------|
| `backend/data/daily_sync.sh` | Header updated to reference infra/cron.txt and specs/db-hosting.md |
| `backend/data/seed/contracts_2025_26.csv` | Expanded 514-player coverage with `source` column |
| `backend/services/salary_ingestion_service.py` | Per-row source read from CSV; flush+try/except bulk fix |
| `backend/models/trade.py` | `salary_source` field on `TeamContractEntry` |
| `backend/routers/trade.py` | Pass `contract.source` as `salary_source` |
| `frontend/src/lib/types.ts` | `salary_source` on `TeamContractEntry` interface |
| `frontend/src/app/trade-machine/page.tsx` | `est.` badge + panel banner |
| `backend/tests/test_schema_migrations.py` | Head revision assertion updated to 0017 |
| `CLAUDE.md` | Sprint 80 added to Recent Sprints |
| `specs/BACKLOG.md` | Sprint 81 candidates added |
| `specs/sprint-history.md` | Sprint 79 + 80 archived |

---

## Verification

| Check | Result |
|-------|--------|
| Migration row count | PASS: 50 tables, 4,558,469 rows |
| Alembic version on Hetzner | `0017_sprint80_raw_payload_ttl` |
| `/api/leaderboards/teams` | 200 OK |
| `/api/trade/contracts/BOS` | 200 OK, $241,196,500 team total |
| `/api/playoffs/today` | 200 OK |
| VM daily_sync dry-run | season=2025-26, is_playoffs=0, all steps listed correctly |
| R2 backup manual trigger | `bip-20260430.dump.gz` confirmed in bucket (140 MB) |
| Port 5432 firewall | Reachable from laptop IP only |
| `npx tsc --noEmit` | Clean |

---

## Remaining Post-Sprint Items

| Item | Owner | Notes |
|------|-------|-------|
| Disable laptop cron | Vivek | `crontab -e` on Mac, comment out the two `daily_sync.sh` entries |
| Monitor first automated 6am sync | Vivek | `ssh root@5.78.114.15 && tail -f /var/log/bip-sync.log` |
| `play_by_play` legacy table retirement | Sprint 81 | Migrate 11+ readers to `play_by_play_events` |
| FastAPI public deploy | Sprint 81 | Render/Railway/fly.io, same DATABASE_URL env var |

---

## Lessons

- `awscli` is not in Ubuntu 24.04 apt repos — install via `pip3 install awscli --break-system-packages`
- `python3.12-venv` must be installed separately before `python3 -m venv` works on Ubuntu 24.04
- Env file sourcing in cron requires `. /etc/bip/env` with `set -a` pre-declared (or the dot-source after `set -a` in the script) — bare `. /etc/bip/env` does not export variables to child processes
- Fresh `pg_restore` tables are smaller than live DB tables (no bloat) — size mismatches in `verify_migration.py` are expected; only row-count mismatches are a red flag; use `--byte-pct-tolerance 1.0` to confirm
- Hetzner defaults to `root` user, not `ubuntu` — `ssh root@<ip>` not `ssh ubuntu@<ip>`
