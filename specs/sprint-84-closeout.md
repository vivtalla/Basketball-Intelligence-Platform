# Sprint 84 Closeout — Production Deploy + Workflow Reset

**Sprint:** 84
**Date:** 2026-05-02
**Owner:** Claude (with Vivek's web-UI clicks for Hetzner / Cloudflare / Vercel)
**Status:** Final

---

## Shipped

Two-stage sprint executed in one session.

### Stage 1 — VM deploy (Sprints 82+83 hangover, finally executed)

**Phase 0 — SSH access recovery (rescue mode)**
- Hetzner Cloud Console rescue mode enabled with Vivek's SSH key (`vivek-macbook` / `~/.ssh/id_ed25519.pub`)
- First attempt failed: wrote authorized_keys to `/mnt/home/ubuntu/.ssh/` without first mounting the real disk → wrote to the rescue OS's tmpfs, vanished on reboot
- Second attempt: `mount /dev/sda1 /mnt`, then bind-mounted `/proc`, `/sys`, `/dev` and `chroot /mnt /bin/bash` to:
  1. Create the missing `ubuntu` user (no entry in `/etc/passwd` despite `/home/ubuntu/bip` existing — likely from a previous rebuild) with `useradd --uid 1000 --gid 1000 --no-create-home --shell /bin/bash ubuntu`
  2. Add to sudo group + `/etc/sudoers.d/ubuntu` with NOPASSWD
  3. Enable SSH service via `ln -sf /lib/systemd/system/ssh.service /etc/systemd/system/multi-user.target.wants/ssh.service` (the symlink was missing — root cause of why SSH was refusing connections after the previous reboot)
  4. Fix `/home/ubuntu` ownership to `ubuntu:ubuntu` (was `root:root`)
- Power cycle out of rescue → `ssh ubuntu@5.78.114.15 'echo OK'` works

**Phase 1 — Firewall**
- Hetzner Cloud firewall: added inbound TCP 80 + 443 from `0.0.0.0/0, ::/0`
- Port 5432 (Postgres) stays locked to laptop IP only

**Phase 2 — Domain + DNS**
- Registered `courtvue.app` via Cloudflare Domain Registration ($14.20/yr — `.com` was taken)
- Added DNS records (all proxied/orange-cloud):
  - `api` A → `5.78.114.15`
  - `@` CNAME → `cname.vercel-dns.com`
  - `www` CNAME → `cname.vercel-dns.com`

**Phase 3 — Backend deploy**
- `git pull origin master` on VM (pulled `4348eea` Sprint 83 closeout)
- `sudo bash infra/caddy-install.sh` — installed Caddy from official apt repo, copied Caddyfile + bip-api.service, enabled both
- Wrote `/etc/bip/env`:
  ```
  NBA_API_USER_FETCH_DISABLED=true
  CORS_ORIGINS=https://courtvue.app,https://www.courtvue.app
  DATABASE_URL=postgresql://bip:<password>@localhost/bip
  ```
- Ran `ALTER USER bip WITH PASSWORD '<password>'` in psql (the `bip` Postgres user existed but had no password, and no `DATABASE_URL` was set — would have caused 500s on every endpoint)
- `./venv/bin/pip install gunicorn==23.0.0`
- `./venv/bin/python -m alembic upgrade head` — clean
- `sudo systemctl start bip-api && sudo systemctl reload caddy`
- Caddy obtained Let's Encrypt cert for `api.courtvue.app` automatically (~3 sec)
- `curl -sf https://api.courtvue.app/api/health` → `{"status":"ok"}`

**Phase 4 — Vercel**
- Imported GitHub repo
- Root Directory: `frontend/` (critical — defaults to repo root which would fail)
- Env var: `NEXT_PUBLIC_API_URL=https://api.courtvue.app` (Production, Preview, Development)
- First deploy failed during prerendering of `/bracket` — Next.js 14+ requires `useSearchParams()` to be wrapped in `<Suspense>` or it errors during static generation
- **Fix shipped as `43b7a4a`:** wrapped the page-level component in 3 files in `<Suspense>`:
  - `frontend/src/app/bracket/page.tsx`
  - `frontend/src/app/games/[gameId]/page.tsx`
  - `frontend/src/app/teams/[abbr]/page.tsx`
  - The other 5 pages using `useSearchParams` (insights, pre-read, leaderboards, player-stats, compare) already had Suspense wrappers
- Local `npm run build` clean after fix; pushed; Vercel auto-rebuilt and went green
- Custom domains added: `courtvue.app` + `www.courtvue.app`

**Phase 5 — Cloudflare WAF + cache**
- 5 Cache Rules created (all use "Ignore cache-control header and use this TTL"):
  - Playoffs: hostname=api.courtvue.app AND URI starts with /api/playoffs/ → 2 hr
  - Standings: /api/standings → 2 hr
  - Leaderboards: /api/leaderboards → 6 hr
  - Player splits: /api/players/ → 12 hr
  - Default catch-all: hostname=api.courtvue.app → 2 hr (lowest priority)
- 1 WAF Custom Rule (Block): `(http.user_agent eq "") or (http.user_agent contains "zgrab") or (http.user_agent contains "masscan")`

**Phase 6 — Smoke test**
- Frontend: 200, ~145ms first byte from local laptop
- API health: 200 in ~52ms
- Leaderboards: 200, real data, ~191ms (cold cache)
- Standings: 200
- Player search: 200
- Vivek confirmed full site loads on phone, all panels populate, bracket pre-selects via `?series_id=X` deep link

### Stage 2 — Workflow reset (this closeout's other half)

**`AGENTS.md` rewrite:**
- New top-level **Sprint Workflow** section with 8 explicit phases (Plan → Implement → QA → Pre-merge Verification → Merge → Deploy → Production Smoke Test → Closeout)
- New **Pre-merge Verification Checklist** — 9-item gate before any master push
- New **Production Deploy Procedure** — frontend automatic via Vercel; backend manual via `infra/deploy.sh` (with `--migrate` flag for schema changes)
- New **Rollback Procedures** — frontend (Vercel one-click promote), backend (git checkout + deploy.sh), migrations (alembic downgrade -1), cache invalidation (Cloudflare Purge Everything)
- Updated **Session Start Checklist** — now includes mandatory 5-second production health check
- Updated **Sprint Closeout Checklist** — added deploy + smoke test as steps 9-11
- Removed the "Pending hangover from Sprint 82+83" block (deploy is done)
- Sprint Status table reset to Sprint 85 awaiting kickoff

**`CLAUDE.md` updates:**
- New **Production** section after Tech Stack: live URLs, VM details, edge layer, service stack, where secrets live
- New **Production Deploy** subsection in Commands: SSH commands for backend deploy, journalctl/systemctl inspection, cache purge
- New **Production Safety** section after Caching Strategy: 7 rules covering auto-deploy implications, API contract changes, schema migrations, cache TTLs, CORS, secrets, rollback availability
- Sprint 84 entry added to **Recent Sprints**; Sprint 82 moved to history

---

## Deferred / Not finished

Carried from Sprint 83:
- **OG image polish** — current `/og` route is workmanlike but not bespoke. BACKLOG.
- **Bracket auto-advancement** — winner advances into next-round empty slot. Real feature, not polish. BACKLOG.
- **Per-series detail page** — Vivek's "fully fleshed out tracker." Sprint 83c routed Story Rail tiles to `/bracket?series_id=X` (Playoff Command Center), which is largely that page; a focused per-series surface with player game-by-game stat tables remains a separate effort. BACKLOG.
- **Lint cleanup pass** — 4 pre-existing errors in `draft/` + `trade-machine/`. BACKLOG.

New from Sprint 84:
- **Tracking / hustle / passing dashboards** — third and fourth official data domains from the matrix. Carried from Sprint 83, still on BACKLOG.

---

## Coordination Lessons

- **Rescue-mode disk recovery requires mounting the real disk first.** First attempt wrote to `/mnt/home/ubuntu/.ssh/` without `mount /dev/sda1 /mnt` — wrote to the rescue OS's tmpfs, which vanished on reboot. ~30 min wasted. Going forward: any rescue-mode work that touches the real filesystem must `mount /dev/sda1 /mnt` first, and to actually create users / enable services on the real disk requires `chroot /mnt` with `/proc`, `/sys`, `/dev` bind-mounted. Documented in `infra/README.md` (or should be added).
- **Vercel auto-deploy on push to master is now real.** The mental model "push to master = done" no longer holds. Push to master = frontend deploys to production within ~2 min (success or visible error in Vercel dashboard), and backend still needs a manual deploy step. The new Sprint Workflow phases make this explicit.
- **Postgres user existed but had no password.** A fresh deployment to a VM that had a partial prior setup needs to validate not just that the user exists but that auth actually works. Future: add a smoke check to `infra/deploy.sh` that does a one-row test query before the systemd restart.

## Workflow Lessons

- **Deploy execution belongs in plan mode, not chat.** This sprint's deploy was guided ad-hoc. With the new 8-phase workflow, future deploys have a documented Phase 6 with a known runbook — no improvisation needed.
- **The QA phase (Phase 3) is new for a reason.** Previously, "tests pass + build succeeds" was treated as the gate. The Vercel build failure on `useSearchParams` proved that `npm run build` catches things `npm run dev` doesn't — specifically Next.js 14+ static generation strictness. Phase 3 now explicitly requires `npm run build` (not just `npm run dev`).
- **Pre-merge Verification Checklist is one place, not scattered.** Previously, "what to check before merge" was distributed across CLAUDE.md, AGENTS.md, and tribal knowledge. Now it's one checklist in AGENTS.md that every closeout walks through.

## Technical Lessons

- **Next.js 14+ requires `<Suspense>` around any client component that uses `useSearchParams()`.** Otherwise the production build fails during prerendering with "Export encountered an error on /<page>". Dev mode silently allows it. Pattern: extract the existing component as `<Page>Inner`, then make the default export a thin wrapper that renders `<Suspense fallback={<Skeleton/>}><PageInner/></Suspense>`.
- **Cloudflare Cache Rules input TTL is in hours (minimum 2), not seconds, in the current UI.** The runbook's seconds-based TTLs from `infra/README.md` need to be reinterpreted as hours when entered. Updated that mapping in this closeout.
- **Caddy + Let's Encrypt is friction-free behind Cloudflare orange-cloud.** Cert obtained in ~3 sec via HTTP-01 challenge. No DNS-01 wrangling required.
- **`pg_hba.conf` on Hetzner Ubuntu cloud images uses `scram-sha-256` for localhost connections.** Peer auth only works for Unix socket connections from a matching system user. Backend services using `postgresql://` URLs go via TCP and need a real password.
- **`/etc/bip/env` permissions matter.** Created with `sudo tee` defaults to root-only readable; need `sudo chmod 644` for the ubuntu-owned `bip-api.service` to source it.

## Next Sprint Seeds (Sprint 85)

1. **Tracking / hustle / passing dashboards** — third and fourth official data domains. Mirror Sprint 81 B3 pattern.
2. **OG image polish** — load real fonts into Satori, consider stat callouts, parameterize for per-page share cards.
3. **Bracket auto-advancement** — winner-advances logic + next-round empty-slot rendering. Requires `parent_series_id` + `slot_position` columns on `PlayoffSeries` (Alembic migration).
4. **Per-series detail page** — fully-fleshed tracker with player game-by-game stat tables and `/games/[gameId]` click-through.
5. **Lint cleanup pass** — fix the 4 pre-existing errors in `draft/` and `trade-machine/`, the flaky Monte Carlo test, add `localStorage.setItem` defensive-wrapper lint rule.
6. **First sprint under the new workflow** — exercise the full 8-phase flow including Production Smoke Test on a real feature merge to validate the docs hold up in practice.

## Backlog Refresh

- Removed: "Execute the pending VM deploy" — done.
- Carried: OG image polish, bracket auto-advancement, per-series detail page, lint cleanup pass, tracking/hustle/passing dashboards, Spotrac retry, award cohort expansion, flaky Monte Carlo test.
- New: none specific to this sprint (workflow updates live in AGENTS.md and CLAUDE.md, not BACKLOG).
