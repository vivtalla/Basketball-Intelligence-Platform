# Sprint 87 Closeout — Security Maintenance Pass

**Sprint:** 87
**Date:** 2026-05-03
**Owner:** Claude (single sequential stream, main session)
**Status:** Final

---

## Shipped

Security audit findings from the post-Sprint-86 review, executed end-to-end under the new Deferral Policy. Single branch (`feature/sprint-87-security-maintenance`), 6 per-stream commits, deployed cleanly. Production smoke verified all changes live.

500 backend tests still pass (no regression from FastAPI 0.115→0.124 or Starlette 0.41→0.44 framework bumps). `npm run build` clean, `npm run lint` 0 errors / 0 warnings (Sprint 85 baseline maintained).

### Stream A — npm vulnerability fix (`a6d51a7`)
- `npm audit fix` (non-breaking) cleared 1 vuln; `npm audit fix --force` cleared the high-severity Next.js DoS by bumping `next 16.2.0 → 16.2.4` (past the affected `<16.2.3` range). Resolved CVEs: GHSA-q4gf-8mx6-v5v3 (Next DoS via Server Components, CVSS 7.5), GHSA-f886-m6hf-6m8v (brace-expansion DoS).
- 3 moderate vulns remain — all from postcss bundled inside Next.js (CSS Stringify Output XSS, GHSA-qx2v-qp2m-jg93). `npm audit fix --force` would downgrade Next 16 → 9.3.3 (7 majors back) which is absurd. Accepted because: (1) the practical exploit surface is zero (we don't pass user-controlled CSS through postcss serialization; Tailwind generates static CSS at build time), (2) Next.js needs to upgrade their bundled postcss upstream — out of our control. Documented in this closeout.
- Verification: `npm run build` succeeds (catches Suspense / Server Components / ImageResponse paths); `npm run lint` 0 errors.

### Stream B1 — Safe Python dependency patches (`9812870`)
- `pydantic 2.10.4 → 2.10.6`, `sqlalchemy 2.0.36 → 2.0.49`, `pypdf 5.4.0 → 5.9.0`. All three are within their major version line; zero breaking changes.
- Other 10 outdated packages (certifi, charset-normalizer, idna, Mako, packaging, pyee, setuptools, starlette, tzdata) are transitive deps that will auto-upgrade when their parent packages reinstall on production. None had known CVEs flagged by audit.
- Verification: 500/500 tests pass.

### Stream B2 — FastAPI + Starlette major bumps (`bd65b74`)
- `fastapi 0.115.6 → 0.124.4` (9 minor versions). Read CHANGELOG between releases for breaking changes; pre-1.0 framework so risk is real. **Outcome:** zero regressions in our 500-test suite. No router signatures broke, no dependency-injection patterns affected, all 193 routes still register.
- `starlette 0.41.3 → 0.44.0` pinned explicitly (pulled in by FastAPI but pinning prevents drift).
- Verification: 500/500 tests pass post-upgrade.

### Stream C1 — CORS hardening (`0f6d70b`)
- `backend/main.py:50-56` — `allow_methods=["*"]` → `["GET", "HEAD", "POST", "OPTIONS"]`. The platform has 40 POST + 2 PATCH + 2 DELETE endpoints, but PATCH/DELETE are admin-only and never called from a browser — dropping them tightens the surface without breaking any user-facing feature.
- `allow_headers=["*"]` → `["Content-Type", "Accept", "Authorization"]`. Authorization included as future-proof no-op for any auth-bearing endpoint.
- Verification (production): CORS preflight returns the tightened allowlist:
  - `access-control-allow-methods: GET, HEAD, POST, OPTIONS`
  - `access-control-allow-headers: Accept, Accept-Language, Authorization, Content-Language, Content-Type` (Starlette's CORS middleware automatically adds Accept-Language + Content-Language to any custom list, which is fine — those are safe)

### Stream C2 — Gunicorn file log + logrotate (`4944251`)
- `infra/bip-api.service`: changed `--access-logfile -` to `--access-logfile /var/log/bip-api/access.log`. Added `ExecStartPre=+/usr/bin/install -d -o ubuntu -g ubuntu -m 0755 /var/log/bip-api` so the dir is auto-created (with `+` to run as root).
- New `infra/bip-api.logrotate`: 14-day retention, daily rotation, copytruncate, compress.
- `infra/README.md`: added one-time install instructions + R2 backup lifecycle deferral note.
- Production install: `sudo cp infra/bip-api.logrotate /etc/logrotate.d/bip-api && logrotate -d` validated. **Required manual `sudo systemctl daemon-reload` after `cp` of the .service file** because `infra/deploy.sh` only copies the service unit during the one-time `caddy-install.sh` bootstrap, not on routine deploys. Worth fixing in a future infra-touch sprint.

### Stream C3 — PGPASSWORD comment cleanup (REJECTED on review)
- The audit flagged `infra/bip-backup.sh:14` for mentioning `PGPASSWORD` in a parenthetical: `PGUSER, PGDATABASE — Postgres connection (PGPASSWORD via .pgpass)`.
- **On review, this is accurate documentation, not a security risk.** The comment explains how the auth works — `.pgpass` is the actual mechanism, with PGPASSWORD mentioned as the env-var equivalent we deliberately don't use (it would leak via `ps` listings). Removing the comment makes the documentation worse, not better.
- Documented as "audit finding rejected on review" — good engineering practice not to action-item every audit finding without judgment.

### Bonus: GitHub repo made public mid-sprint (Vivek-side decision)
- During Phase 6 deploy, `git pull` on the VM failed with "could not read Username for 'https://github.com'" because the repo was private and no credentials were cached on the VM. Previous Sprint 84/85/86 deploys had worked through a temporary credential cache that had expired.
- Rather than set up a deploy key or PAT, Vivek made the repo public — appropriate for a public-facing platform with no proprietary code. Subsequent `git pull` worked without auth.

---

## Deferred (with `Why deferred:`)

### R2 backup lifecycle rule
**Why deferred:** Cloudflare R2 dashboard UI configuration step, not code. Per Deferral Policy "different domain" — infra UI config done outside the code repo. The audit recommended adding a 90-day auto-delete lifecycle rule as a second-layer safety net beyond the existing `bip-backup-prune.sh` shell logic. Documented in `infra/README.md` as a one-time op for the next Cloudflare-touch session.

**Everything else from the security audit shipped, was rejected on review, or is documented above.**

---

## Coordination Lessons

- **Single-stream sprint with sequential commits worked well for maintenance work.** No subagents needed because each stream was small enough to do directly without context overhead. Total wall-clock: ~45 min for streams A→C2.
- **The audit finding "review" step was important.** Stream C3 (PGPASSWORD cleanup) was on the original plan but rejected on inspection — the parenthetical comment was accurate documentation. The Deferral Policy doesn't say "do everything on the audit list" — it says "do everything that needs doing." This sprint exercised that judgment.

## Workflow Lessons

- **`infra/deploy.sh` does NOT auto-sync `bip-api.service` to systemd.** Sprint 84's `caddy-install.sh` is the one-time bootstrap that copies the service unit. Subsequent service-unit changes (Sprint 87 Stream C2 added an `ExecStartPre`) require a manual `sudo cp infra/bip-api.service /etc/systemd/system/ && sudo systemctl daemon-reload`. Worth fixing in `deploy.sh` to detect drift and re-install the unit automatically — file as a Sprint 88 candidate.
- **GitHub repo visibility matters for VM deploys.** The temporary credential cache that worked through Sprint 86 silently expired between Sprint 86 hotfix and Sprint 87 deploy. Public repo is now the auth strategy; if it ever needs to go private again, set up an SSH deploy key on the VM at the same time.
- **The Pre-merge Verification Checklist's "no schema changes" check was N/A for this sprint, but the FastAPI bump catches a subtle issue:** if `fastapi 0.124.4` had broken any of our routers' signatures, only `pytest` would have caught it (mypy / type checking would not). The 500-test suite is the safety net for framework bumps.

## Technical Lessons

- **`npm audit fix --force` can suggest absurd downgrades.** It tried to fix the postcss XSS by reverting Next 16 → 9.3.3. Always inspect what `--force` will do before accepting it. The right move was to accept the moderate (no real exploit surface for our use) rather than break the entire frontend.
- **CORS middleware automatically adds standard headers.** Starlette's CORS adds `Accept-Language` and `Content-Language` to the allow-headers list even when not specified — they're considered always-safe. The actual enforced allowlist on the wire was: `Accept, Accept-Language, Authorization, Content-Language, Content-Type`.
- **systemd service unit changes need explicit re-install + daemon-reload.** `infra/deploy.sh` reloads Caddy and restarts bip-api but does NOT re-install service unit files. Future-proof: add `cp + daemon-reload` to deploy.sh, or use systemd template units that read from a config file.
- **3 moderate npm vulns pinned in transitive deps inside Next.js are not always fixable on our end.** The remaining postcss XSS will resolve when Next.js upgrades their bundled postcss. Worth monitoring `npm audit` periodically (every sprint?) to see if Next's new releases pull in fixed versions.

## Next Sprint Seeds (Sprint 88 — TBD)

No obvious Sprint 88 candidates from this sprint specifically. Sprint 86's R2 lifecycle deferral remains. From this sprint:
- Fix `infra/deploy.sh` to auto-install `bip-api.service` + daemon-reload on changes (workflow gap surfaced this sprint, not yet fixed)
- Periodic `npm audit` + `pip list --outdated` review, maybe quarterly

## Backlog Refresh

Removed (shipped in Sprint 87):
- npm vulnerabilities (high Next.js DoS resolved; 3 moderate Next-bundled postcss accepted)
- 13 outdated Python packages (3 explicit pins bumped; rest auto-upgrade as transitive deps on production reinstall)
- CORS overly permissive (tightened to specific methods + headers)
- Gunicorn access log only in journal (now also in `/var/log/bip-api/access.log` with logrotate)

Removed (rejected on review, with documented rationale):
- PGPASSWORD comment cleanup — accurate documentation, not unused code

Carried (legitimate deferral, infra UI domain):
- R2 backup lifecycle rule

New (workflow gap surfaced this sprint):
- `infra/deploy.sh` auto-install of service units + daemon-reload
