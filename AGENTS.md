# Agent Coordination

Last updated: 2026-05-08 by Claude (Sprint 94 closeout — On/Off Impact Command Center: side-of-ball decomposition, classification, confidence tiers, lineup context, external validation on both leaderboard and player profile)

> Both agents read this file before touching code at the start of every session.
> The canonical source of truth is the clean `master` checkout at `/Users/viv/Documents/Basketball Intelligence Platform`.
> If a future session starts from another branch or worktree, return to this canonical root first unless the sprint explicitly says otherwise.
> All new sprint implementation happens on sprint branches/worktrees, never directly on `master`.
> At sprint close, update the sprint closeout note, refresh `specs/BACKLOG.md`, reset this file for the next sprint, and update the sprint summary in `CLAUDE.md`.

---

## Sprint Status

| Field | Value |
|-------|-------|
| Sprint | 95 |
| Goal | TBD — awaiting Vivek's sprint kickoff |
| Started | TBD |
| Target merge | TBD |
| Sprint shape | TBD |
| Branch | `master` until Sprint 95 kickoff |
| Worker policy | No active sprint; set at kickoff |

**Production status:** CourtVue Labs is publicly live at `https://courtvue.app` (Vercel) + `https://api.courtvue.app` (Hetzner CPX11, `ubuntu@5.78.114.15`). Sprint 94 shipped the On/Off Impact Command Center: side-of-ball decomposition (ORTG Δ / DRTG Δ), impact classification (Two-Way Elite / Offensive Engine / Defensive Anchor / Liability / Neutral), confidence tiers, lineup context (top/worst 3 five-man lineups), and external validation (RAPM/EPM/PIPM) on both the enhanced leaderboard and individual player profile. 552 backend tests (was 513, +17 new + prior sprint tests), 0 lint errors. 2 genuine deferrals remain: R2 backup lifecycle (Cloudflare UI, ~5 min) and MVP voter calibration cohort expansion (data-blocked).

---

## Sprint Workflow

Every sprint follows these 8 phases. The QA, Pre-merge Verification, Deploy, and Production Smoke Test phases became standard at Sprint 84 — they exist because the platform is now live and master pushes auto-deploy the frontend to production within ~2 minutes.

### Phase 1 — Plan
- Architect spec written into `~/.claude/plans/<plan-name>.md`
- Files to touch identified up-front; **Shared File Lock Table** updated for shared files
- Verification approach defined per stream
- Sprint shape (single sequential, two-team parallel, etc.) chosen and documented in the Sprint Status table above
- **Scope for completeness, not for time** (see **Deferral Policy** below). Each stream's "Done" criteria captures the full feature in its final state — sortable columns included if the table needs sorting, backfill scripts included if a migration creates data drift, frontend label richness included if it's part of the user-facing experience. Plans should NOT have a "deferred polish" section unless one of the approved deferral reasons applies. If the work is bigger than expected, lengthen the sprint — don't ship the 60% solution.

### Phase 2 — Implement
- Each stream commits to its sprint branch in its own worktree (never directly on `master`)
- Per-item commits where the diff allows (overlapping files may collapse to one commit per stream)
- Workers spawned per the **Worker Deployment Rules** below — bounded, independent subtasks only

### Phase 3 — QA (~30-60 min)
- Run the full backend test suite: `cd backend && pytest -q` — must pass
- Run frontend production build: `cd frontend && npm run build` — must succeed (catches Suspense / SSR errors that dev mode hides)
- Run lint: `cd frontend && npm run lint` — no NEW errors (4 pre-existing errors in `draft/` and `trade-machine/` are documented in BACKLOG)
- Manual smoke walkthrough in a browser of every surface the sprint touched: golden path + one edge case + a quick mobile-viewport spot check if UI changed
- For backend changes: hit the new endpoints with `curl` against the local dev server (`http://localhost:8000`) to confirm response shapes

### Phase 4 — Pre-merge Verification
Run through the **Pre-merge Verification Checklist** below. Anything red means stop and fix before merging.

### Phase 5 — Merge to master
- Sprint branch fast-forwards or merges into local `master`
- `git push origin master`
- Vercel detects the push and starts building the frontend automatically (~2 min)

### Phase 6 — Deploy
- **Frontend**: nothing to do — Vercel auto-deploys on the master push. Verify at vercel.com → Deployments → confirm the latest commit shows "Ready" status. If "Error", click into the deployment → View Build Logs → fix locally and push again. The previous deployment stays live until a new one succeeds — production is never broken by a failed build.
- **Backend**: manual.
  ```bash
  ssh ubuntu@5.78.114.15
  cd /home/ubuntu/bip && git pull origin master
  sudo bash infra/deploy.sh                # standard deploy
  # OR
  sudo bash infra/deploy.sh --migrate      # if any Alembic revisions are new
  ```
  Script exits non-zero if `/api/health` doesn't return 200 — investigate before declaring deploy complete.

### Phase 7 — Production Smoke Test
After deploy:
```bash
curl -sf https://api.courtvue.app/api/health           # 200, returns {"status":"ok"}
curl -sf "https://api.courtvue.app/api/<one-changed-endpoint>"  # 200 + valid JSON
curl -sI https://courtvue.app | head -3                # 200 or 307 (redirect to www is fine)
```
Then load `https://courtvue.app` in a real browser and walk through the changed surface end-to-end. If anything is broken, run the **Rollback Procedures** for the affected layer immediately.

### Phase 8 — Closeout
Use the **Sprint Closeout Checklist** below.

---

## Deferral Policy

**Default: don't defer. Sprints ship features in their final state.** If a feature has obvious follow-on polish ("add sortable columns later," "richer labels later," "backfill existing rows later"), that work belongs in the same sprint that ships the feature, not the next one.

The trap to avoid: treating every sprint as a 60%-complete MVP with a tail of follow-ons. That makes the BACKLOG grow faster than it shrinks and leaves users with half-baked features stacked on top of each other. Better to ship one fully-finished thing per sprint than three half-finished things.

**Sprints are scoped, not capped.** If a complete feature needs 12 hours of work, the sprint is 12 hours. Don't ship 6 hours and defer 6 — either tighten the scope so the 6 hours produces something genuinely complete, or commit to the full 12. Length is fine; half-baked is not.

**Deferral is acceptable only when:**

1. **Blocked on data we don't have yet** — e.g. waiting on the next nightly NBA sync, waiting on a season to start, waiting on Spotrac to populate contract rows
2. **Blocked on infrastructure we don't have yet** — e.g. requires a new managed Postgres instance, a new third-party service signup, a Cloudflare paid-tier feature
3. **Blocked on a user decision we haven't made** — e.g. design direction, methodology choice, naming
4. **Genuinely a different domain** — e.g. shipping the player-tracking dashboards doesn't obligate the same sprint to ship team-tracking; those are sister features that warrant their own sprint shape, not "follow-on polish"

If a deferral doesn't fit one of those reasons, it's not a deferral — it's incomplete work. Lengthen the sprint instead.

**When you do defer, document why in the closeout.** The Sprint Closeout Checklist now requires a "Why deferred" line per item with one of the four approved reasons. If you can't write it cleanly, the work isn't actually blocked — it's just unfinished, and you should finish it before closeout.

---

## Pre-merge Verification Checklist

Before merging any sprint branch into `master`, every item below must be green. A merged push deploys to production via Vercel within ~2 minutes — there is no staging gate.

- [ ] All backend tests pass: `cd backend && pytest -q`
- [ ] Frontend production build succeeds: `cd frontend && npm run build`
- [ ] No new ESLint errors: `cd frontend && npm run lint` (4 pre-existing errors in `draft/` and `trade-machine/` are documented and OK)
- [ ] Manual smoke walkthrough completed for every changed surface (golden path + one edge case)
- [ ] If schema changed: Alembic migration created, runs cleanly on local DB, and `--migrate` flag noted in the deploy plan
- [ ] If API contract changed: every frontend caller updated in the same sprint (search for the endpoint or field name across `frontend/src/`)
- [ ] If a new endpoint added: confirm CORS origin allows it (no change needed for `courtvue.app` / `www.courtvue.app`), confirm Cloudflare cache rule TTL is sensible (add a new rule or rely on the 2hr catch-all)
- [ ] If a new `nba_client` wrapper added: `_block_live_fetch_if_user_mode("<method>", cache_key)` is called immediately after the cache-miss check, before any network IO. Without it, production user requests trigger live `stats.nba.com` calls that take 3-30 seconds and can OOM the worker. (Sprint 86 hotfix lesson — `1de57c5`.)
- [ ] No secrets, passwords, or production env values in any commit (`git log -p origin/master..HEAD | grep -iE "password|secret|api[_-]key" | head`)
- [ ] Sprint closeout artifact draft started in `specs/sprint-NN-closeout.md`

---

## Production Deploy Procedure

### Frontend — Vercel (automatic)

On push to `master`, Vercel automatically:
1. Detects the new commit
2. Builds the Next.js app from the `frontend/` root
3. Promotes the new build to production at `courtvue.app`

Verify at https://vercel.com → CourtVue project → Deployments. Status should show "Ready" within ~2 min.

### Backend — manual

```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip
git pull origin master
sudo bash infra/deploy.sh                # standard deploy
# OR
sudo bash infra/deploy.sh --migrate      # if any Alembic revisions are new
```

`infra/deploy.sh`:
1. Updates pip dependencies from `backend/requirements.txt`
2. Runs `alembic upgrade head` if `--migrate` is passed
3. Validates the Caddyfile syntax
4. Reloads Caddy
5. Restarts `bip-api.service`
6. Health-checks `http://127.0.0.1:8000/api/health` — exits 1 if non-200

If the script fails, inspect:
```bash
sudo journalctl -u bip-api -n 100 --no-pager
sudo journalctl -u caddy -n 50 --no-pager
sudo systemctl status bip-api caddy
```

---

## Rollback Procedures

### Frontend rollback (Vercel)
1. Vercel dashboard → CourtVue project → Deployments
2. Find the last known-good deployment (most recent "Ready" before the bad one)
3. Click the three-dot menu → **Promote to Production**
4. Production cuts over within seconds — no rebuild needed

### Backend rollback (VM)
```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip
git log --oneline -5                     # find the previous good SHA
git checkout <prev-sha>
sudo bash infra/deploy.sh
```
Re-deploy a forward fix later by `git checkout master && sudo bash infra/deploy.sh`.

### Migration rollback
```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip/backend
source /etc/bip/env
./venv/bin/python -m alembic downgrade -1   # roll back one revision
```
Always test downgrade locally before deploying any forward migration.

### Cache invalidation
When a fix landed but users still see stale data: Cloudflare dashboard → courtvue.app zone → Caching → Configuration → **Purge Everything**. Forces all 5 cache rules to refetch from origin on next request. Use sparingly — every purge increases load on the VM.

---

## Canonical Workspace

- Canonical repo root: `/Users/viv/Documents/Basketball Intelligence Platform`
- Canonical branch: `master`
- Canonical remote: `origin/master`
- Extra temporary worktrees should only exist during an active sprint and must be removed at sprint close

If repo state, sprint numbering, or shipped features appear to disagree across locations, trust this workspace on `master` first and reconcile from there.

---

## Current Assignments

### Claude
- Branch: TBD at kickoff
- Scope: No active sprint assignment
- Status: Not started

### Codex
- Branch: TBD at kickoff
- Scope: No active sprint assignment
- Status: Not started

---

## Shared File Lock Table

Claim a shared file here before editing. If a file is already claimed, read that branch before planning and do not edit until the claim is released or the work merges.

`frontend/src/lib/types.ts` and `frontend/src/lib/api.ts` are append-only.
`backend/db/models.py` and `backend/db/ensure_schema.py` are always claimed together.

| File | Claimed by | Purpose |
|------|------------|---------|
| — | — | No active claims; claim here at the next sprint kickoff before editing shared files |

---

## Handoff Queue

Specs or review notes written by one stream for another. Check this before starting work.

| Spec file | From | To | Status |
|-----------|------|----|--------|
| `specs/data-architecture.md` | Sprint 26 | Next sprint | Reference — read before touching data layer |
| `specs/sprint-55-closeout.md` | Sprint 55 | Next sprint | Reference — Shot Lab Intelligence baseline |
| `specs/sprint-history.md` | Sprint 60 | Next sprint | Reference — Sprint 60 section for X-Ray promotion + explainability parity baseline |
| `specs/sprint-63-closeout.md` | Sprint 63 | Next sprint | Reference — Team/Insights workflow expansion baseline |
| `specs/sprint-65-closeout.md` | Sprint 65 | Next sprint | Reference — Opportunity caching/handoff + scouting inference confidence baseline |
| `specs/methodology-validation.md` | Sprint 71 | Next sprint | Reference — methodology golden fixtures, calibration targets, and validation checks |
| `specs/sprint-84-closeout.md` | Sprint 84 | Next sprint | Reference — production deploy execution + new workflow definitions |
| `specs/sprint-85-closeout.md` | Sprint 85 | Next sprint | Reference — first sprint exercising new workflow; deploy.sh `--migrate` infra fixes; subagent stages, parent commits operating model |
| `specs/sprint-86-closeout.md` | Sprint 86 | Next sprint | Reference — first sprint operating under Deferral Policy; team-level tracking/hustle pattern (12-call multi-measure tracking endpoint); OG image with custom fonts + 5 per-type renderers |
| `specs/sprint-87-closeout.md` | Sprint 87 | Next sprint | Reference — security maintenance pass; FastAPI 0.115→0.124 + Starlette 0.41→0.44 framework bumps with zero regressions; CORS tightened; gunicorn file log + logrotate; lesson re: deploy.sh doesn't auto-install service units |
| `specs/sprint-88-closeout.md` | Sprint 88 | Next sprint | Reference — data foundation audit + full impl: completeness syncs (hustle + tracking populated in reg season), 8 DB indexes, N+1 fixes, cache observability, deploy.sh auto-sync. Honest call: Stream D ISR partial — client pages don't edge-cache, file Sprint 89 candidate. |
| `specs/sprint-89-closeout.md` | Sprint 89 | Next sprint | Reference — team-side player fit on `/teams/[abbr]`: same 3-component math as player-side `team_fit_v3` (45/30/25), inverted (fix team, score many players). Adds self-exclusion for current-roster scoring, team_need_vector (roster-weighted z), position-cohort percentile (display-only). 24h SQLite cache. Workflow lesson: skipped planned "extract internals" refactor — direct import from `team_fit_service` achieves same goal without churn. |
| `specs/sprint-90-closeout.md` | Sprint 90 | Next sprint | Reference — deferred-items cleanup. MVP voter calibration activated end-to-end: per-request live LOO-CV (cached 24h), `MvpCalibrationMetadata` on race response, `runtime_calibration` on methodology registry's `mvp` domain. Opportunity Uplift UI surfaced (UpliftEvidenceCard + row hint + drawer subsection) — Sprint 79 backend has been producing the field for 3 months. Workflow pattern: "static methodology + runtime augmentation" preserves registry as canonical doc while letting callers see live state. Stale BACKLOG entry retired (`/api/health` bypass-cache rule was unnecessary all along). |
| `specs/sprint-94-closeout.md` | Sprint 94 | Next sprint | Reference — On/Off Impact Command Center. Coaching-grade on/off surface: side-of-ball decomposition (ORTG Δ / DRTG Δ), impact classification (5 tiers), confidence tiers, lineup context (LIKE false-positive filter), external validation (RAPM/EPM/PIPM). Enhanced leaderboard + new per-player endpoint. 7 on-off components for player profile. 17 new tests, 552 total. |

---

## Merge Order

TBD at kickoff. Next sprint branch/worktree is created at kickoff and merges back to `master` at closeout.

---

## Sprint Work Allocation

Sprint 87 allocation — TBD at kickoff.

| Area | Files | Owner |
|------|-------|-------|
| — | — | — |

---

## Session Start Checklist

1. Review `tasks/lessons.md` — apply any standing rules before touching code
2. Read this file: canonical root, sprint status, current sprint phase, branch/worktree rules, shared locks
3. Confirm you are in `/Users/viv/Documents/Basketball Intelligence Platform` on `master`, or on the explicitly assigned sprint branch/worktree
4. **Production health check** (5 seconds — required since Sprint 84):
   ```bash
   curl -sf https://api.courtvue.app/api/health
   curl -sI https://courtvue.app | head -1
   ```
   If anything is non-200, raise it with Vivek before starting any new work.
5. Check the **Shared File Lock Table** before editing shared files
6. Check the **Handoff Queue** for any ready spec or review note
7. `git fetch origin` and inspect recent `origin/master`
8. Update your status here if it changed materially
9. Begin work

---

## Worker Deployment Rules

- Use spawned workers only for bounded, independent, non-blocking subtasks
- Do not spawn workers for the immediate blocking task
- Do not spawn workers for vague "explore the codebase" requests
- Every worker prompt must include:
  - exact ownership
  - allowed files or subsystem
  - expected output artifact
  - reminder not to revert others' changes
- Prefer 1-2 workers per sprint track, not unconstrained fan-out
- The main rollout keeps moving on non-overlapping integration work while workers run

---

## Token Efficiency Rules

- Read the minimum files needed before planning or coding
- Prefer one compact architect spec per stream over repeated chat re-explanation
- Keep handoff artifacts short and decision-complete
- Append to shared contracts instead of reshaping them when possible
- Treat `specs/BACKLOG.md` as the durable future-ideas layer; do not rely on long chat history
- Reviews should focus on regressions, contract mismatches, and missing tests before summarizing changes

---

## Branch and Worktree Discipline

- `master` is the only durable source of truth
- Every active sprint branch must have a clearly named worktree
- Every worktree maps to exactly one active branch
- Temporary merge/testing worktrees should be deleted right after merge
- Do not leave a stale feature branch as the default repo root
- At sprint close:
  1. prune merged worktrees
  2. delete merged or superseded local branches
  3. delete merged or superseded remote branches
  4. `git fetch --prune origin`

---

## Sprint Closeout Checklist

1. Stop local dev/test servers started during the sprint and confirm relevant ports/resources are free (`lsof -iTCP:8000`, `lsof -iTCP:3000`, warehouse workers, import jobs, or other long-running processes)
2. Run the full **Pre-merge Verification Checklist** above — every box checked before proceeding
3. **Deferral audit.** Review every "deferred" / "next sprint" / "follow-on" / "future polish" item the sprint surfaced. For each, ask: does it fit one of the 4 approved deferral reasons in the **Deferral Policy** above? If yes, list it in the closeout's "Deferred" section with a one-line "Why deferred:" justification. If no, **do not close out yet** — extend the sprint, finish the work, then come back here.
4. Create or update `specs/sprint-{NN}-closeout.md` with shipped work, deferred work (each with `Why deferred:`), workflow lessons, and next-sprint seeds
5. Refresh `specs/BACKLOG.md` so shipped items are removed or rewritten as follow-ons
6. Reset `AGENTS.md` for the next sprint kickoff state
7. Update `CLAUDE.md` "Recent Sprints" section (keep last 2 sprints inline; move the oldest out to `specs/sprint-history.md`)
8. Append the completed sprint summary to `specs/sprint-history.md`
9. Merge the sprint branch back into `master` locally and push `master` to `origin`
10. **Deploy backend if any backend code changed** (Sprint 84+): ssh into the VM, pull master, run `sudo bash infra/deploy.sh` (or `--migrate` if migrations changed)
11. **Verify frontend deploy** (Sprint 84+): wait ~2 min, check Vercel dashboard for "Ready" status on the new commit
12. **Production smoke test** (Sprint 84+): `curl -sf https://api.courtvue.app/api/health`, load `https://courtvue.app` in a browser, walk through one changed surface end-to-end
13. Confirm `master` contains the sprint closeout commit(s) AND production reflects the new code before declaring the sprint closed

---

## Notes

*Free-form, dated, newest first. Use this for coordination and repo-state exceptions.*

2026-05-08 (Claude): Sprint 94 closed. **On/Off Impact Command Center.** Single branch (`feature/sprint-94-on-off-impact-revamp`), 1 commit, 18 files changed (+1,944/−146). 552 backend tests (was 513, +17 new in `test_on_off_impact_service.py`), `npm run build` clean, `npm run lint` 0/0. Streams: A = 7 new Pydantic models in `models/stats.py` (ImpactClassification + ConfidenceTier enums, OnOffDecomposition, LineupSlot, ExternalValidation, EnhancedOnOffStats, EnhancedLeaderboardEntry, EnhancedOnOffLeaderboardResult). B = `services/on_off_impact_service.py` (NEW) — `_classify_impact` (ORTG/DRTG Δ thresholds ±3), `_confidence_tier` (HIGH ≥800/MEDIUM ≥400/LOW ≥200/INSUFFICIENT), `_lineup_slots_for_player` (LIKE + 3× over-fetch + post-filter false positives by parsing lineup_key), `build_enhanced_on_off` (batched: PlayerOnOff + SeasonStat + Team + TeamSeasonStat + LineupStats + Player), `build_enhanced_on_off_leaderboard` (4 batch queries, no N+1). C = `routers/advanced.py` — leaderboard body replaced with `build_enhanced_on_off_leaderboard()`, response_model upgraded to `EnhancedOnOffLeaderboardResult`; new `GET /{player_id}/on-off-enhanced` endpoint; original `GET /{player_id}/on-off` untouched. G = 17 tests: classify thresholds, confidence tiers, decomposition correctness, lineup LIKE false-positive filter, missing-team-stat graceful handling, RAPM agreement notes (consistent/diverges), 404, leaderboard min-minutes filter, ordering, external metrics surfacing. D = `types.ts` append-only (8 new types/interfaces), `api.ts` 2 new functions, `usePlayerStats.ts` 2 new SWR hooks. E = `/player-stats` on/off tab: 3-button min-minutes toggle (200/400/800), classification filter pills, Quadrant View toggle + `ImpactScatterChart.tsx` (NEW), 9-column sortable table (# / Player+badge / Team / On Min / ORTG Δ / DRTG Δ / On/Off / vs Team / Confidence), click-to-expand rows. F = `PlayerPbpInsights.tsx` on/off grid (lines 200–228) replaced with `<OnOffImpactPanel>`; 7 new `components/on-off/` files (OnOffImpactPanel, OnOffImpactBadge, OnOffConfidenceCallout, OnOffDecompositionBar, OnOffLineupPanel, OnOffExternalValidationPanel, OnOffMethodologyDrawer). `specs/platform-methodology.md` §13 added. **Workflow note:** LIKE false-positive for lineup_key (player 12 matches "112-120-130") is subtle — the 3× over-fetch + post-parse filter pattern handles it cleanly without schema change. **Deferred:** none. Closeout: `specs/sprint-94-closeout.md`.

2026-05-03 (Claude): Sprint 90 closed. **Deferred-items cleanup under the Deferral Policy.** Single sequential branch (`feature/sprint-90-deferred-items`), 4 commits, end-to-end. 513 backend tests (was 509, +4 new in `test_award_calibration.py`), `npm run build` clean, `npm run lint` 0/0. Streams: A1+A2 = `_get_calibration_state(db)` helper in `mvp_service.py` runs `calibrate_award_case_weights(db)` once per request, cached 24h in SQLite (key `award_case_calibration:v1`); `_build_ranked_candidates` uses live weights instead of the module-level `CALIBRATED_AWARD_CASE_WEIGHTS`; new `MvpCalibrationMetadata` Pydantic on `MvpRaceResponse`; new optional `runtime_calibration: Dict` on `MethodologyDomain` populated for `mvp` domain only when `db` is passed (other domains pass through unchanged — generic Dict to avoid coupling). A3 = 4 new integration tests covering activation roundtrip with synthetic 6-season fixtures (asserts pending→False + fitted weights differ + drift cap holds), SQLite cache short-circuit (sentinel + monkey-patched calibrate that raises if invoked), and methodology-registry augmentation (mvp populated, archetype not). B = `types.ts` append-only adds `OpportunityUpliftComparable` + `OpportunityUplift` + `MvpCalibrationMetadata`; new `UpliftEvidenceCard.tsx` mirrors Sprint 58 evidence-card pattern (header + confidence pill, 2-col mean/IQR, top-3 historical comparables, descriptive caveat, empty state for null); mounted full-width below the existing 2x2 grid in `OpportunityDashboard.tsx`; compact one-line uplift hint at row bottom of `OpportunityRow.tsx` (color-toned by sign + tooltip with full IQR); `MethodologyDrawer.tsx` adds collapsible "v2 uplift evidence" subsection. C = `infra/README.md` refined R2 backup lifecycle UI instructions (precise Cloudflare dashboard click order, ~5 min) + cache-stats baseline snapshot (row_count=535, size_bytes=16MB, hit/miss=0 on fresh worker) + retired Sprint 88 deferred `/api/health` bypass-cache rule as not-needed (catch-all 2hr TTL covers it). **Workflow patterns:** "static methodology + runtime augmentation" — registry stays declarative as the canonical methodology document, runtime state surfaces via optional `runtime_calibration` field; let callers see whether the methodology is doing what it documents. Worth reusing as other domains gain calibration steps. **Workflow gotcha:** stale BACKLOG entries become invisible — the `/api/health` bypass-cache rule was filed as Sprint 88 deferred but the README author had explicitly written it was unnecessary. Sat there for a sprint. Lesson: when filing a deferral, link to the docs section that confirms the action; if docs already disagree, don't file the deferral. **Deferred (2 remaining, both genuine):** R2 backup lifecycle (Cloudflare UI, ~5 min — Why: different domain), MVP voter calibration cohort expansion (data-blocked on basketball-reference CSV scrape — Why: blocked on data we don't have). Closeout: `specs/sprint-90-closeout.md`.

2026-05-03 (Claude): Sprint 89 closed. **Team-side player fit on `/teams/[abbr]`.** Single sequential branch (`feature/sprint-89-team-roster-fit`), 4 commits, end-to-end. 509 backend tests (was 500, +9 new in `test_sprint89_team_roster_fit.py`), `npm run build` clean, `npm run lint` 0/0. Streams: A = `services/team_roster_fit_service.py` + `models/team_roster_fit.py` (NEW). Inverts player-side `team_fit_v3` — fix the team, score many players. Reuses `_score_team_fit`, `_team_overlap_flags`, `_build_drivers`, `_feature_team_best`, `_bucket_runway_bonus`, `_position_bucket`, `_confidence_for_team`, `WEIGHTS` from `team_fit_service` directly so player-side and team-side reads use identical math (45/30/25 on 13 z-scored features). Adds **self-exclusion** for current-roster scoring (subject removed from comparison so Role Competition isn't inflated by self-overlap), **`team_need_vector`** (roster-weighted average z per feature, deduped across `SIMILARITY_STATS_V2`'s repeated stl/blk), **position-cohort percentile** (G/F/C — display-only, score formula keeps using global norms so cross-position rankings stay coherent). B = `GET /api/teams/{abbr}/roster-fit` mounted on existing teams router (Sprint 86 inline pattern, no `main.py` change). 24h SQLite cache keyed on `(abbr, season, season_type, limit)`. Cold compute ~1-7s, warm <50ms (verified locally: 2.3s cold, 40ms warm). C = new `fit` tab on `/teams/[abbr]` between `lineups` and `arc`. `TeamRosterFitPanel.tsx` (NEW, 400+ LOC) renders team need vector chips, sortable current-roster table with click-to-expand, league-candidates grid with G/F/C position filter + click-to-expand, methodology drawer with explicit "no salary/availability" disclosure. Reuses player-side `TeamFitPanel` visual language. D = 9 tests covering self-exclusion, position-cohort tagging, low-confidence gating, team-need-vector correctness on a constructed 3-point-poor roster, cache round-trip via Pydantic, 404, determinism, league-candidate exclusion. E = `specs/platform-methodology.md` extended with Team-Side Roster Fit (Sprint 89) subsection under §6. **Workflow lesson:** the planned "extract internals into shared module" refactor commit was skipped — importing `team_fit_service`'s underscore functions directly achieves the same single-source-of-truth without code churn. Don't introduce abstractions ahead of the second caller actually needing them. **Workflow gotcha:** stale `.git/worktrees/bip-s89/index.lock` from a prior aborted session held a corrupted index; `git status` showed thousands of phantom "deleted" files. Removed lock + `git reset HEAD` recovered. Worktree node_modules: don't symlink across canonical → worktree (Turbopack rejects out-of-tree symlinks); just `npm install --prefer-offline` (15 s with cache warm). **Deferred:** none. 4 Sprint 90 candidates filed (salary integration, shot location overlap, defensive scheme clustering, play-type compatibility) — all "different domain" sister features per Deferral Policy. Closeout: `specs/sprint-89-closeout.md`.

2026-05-03 (Claude): Sprint 88 closed. **Data foundation audit + full implementation** under the Deferral Policy. 3 parallel Explore agents (DB structure, caching, sync pipeline) produced comprehensive findings; sequential implementation across single branch. 500 backend tests pass post-impl, `npm run build` clean, `npm run lint` 0/0. **Biggest user win:** player + team hustle and tracking endpoints now return populated data in regular season (was empty 6 months/year — only synced during playoffs). Streams: A = `daily_sync.sh` runs hustle (player + team) + team tracking nightly + new `weekly_sync.sh` runs player tracking Sunday 8am UTC; `gravity_sync_service.sync_player_tracking_stats(player_ids=None)` auto-derives active players from `PlayerGameLog`; production backfill ran post-deploy: 581 player hustle + 30 team hustle + 360 team tracking rows. B1 = Alembic 0023 with 8 missing indexes (season_stats × 2, player_game_logs, play_by_play, lineup_stats, player_on_off, game_player_stats, game_team_stats); defensive `_has_table` + `_has_index` guards. B2 = N+1 fixes in advanced.py top-lineups + on-off-leaderboard + stats.py league-context (position filter pushed to SQL). B3 = SQLAlchemy `pool_size=10, max_overflow=20, pool_recycle=3600`. B4 = weekly Sunday 6am UTC `vacuumdb --analyze-in-stages`. C1 = CacheManager hit/miss/expired counters + new `GET /api/health/cache-stats` endpoint. C2 = `clear_expired()` (returns count) hooked into daily_sync. D = ISR `revalidate` exports added to 6 stable pages (PARTIAL win — client-component pages don't get edge-cached; real fix is server-component refactor, filed as Sprint 89 candidate). E = `infra/deploy.sh` auto-syncs `bip-api.service` + `Caddyfile` with daemon-reload (closes Sprint 87 workflow gap; verified live). Production smoke: hustle/tracking endpoints return populated data (was empty); `/api/health/cache-stats` works; N+1 endpoints 200 in <100ms; `infra/deploy.sh` auto-sync confirmed. Closeout: `specs/sprint-88-closeout.md`.

2026-05-03 (Claude): Sprint 87 closed. **Security maintenance pass under the Deferral Policy.** 6 commits on a single branch (`feature/sprint-87-security-maintenance`) shipped end-to-end. 500 backend tests still pass after FastAPI 0.115→0.124 + Starlette 0.41→0.44 framework bumps (zero regressions in the 193-route surface). `npm run build` clean, `npm run lint` 0/0. Streams: A = `npm audit fix --force` bumped Next 16.2.0→16.2.4 (resolved high-severity DoS GHSA-q4gf-8mx6-v5v3); 3 moderate postcss-bundled-by-Next vulns accepted (no real exploit surface — Tailwind generates static CSS, not runtime user input). B1 = pydantic 2.10.4→2.10.6 + sqlalchemy 2.0.36→2.0.49 + pypdf 5.4.0→5.9.0 (safe patches). B2 = fastapi + starlette major bumps. C1 = CORS tightened: `methods=["*"]` → `["GET","HEAD","POST","OPTIONS"]`, `headers=["*"]` → `["Content-Type","Accept","Authorization"]`. C2 = gunicorn `--access-logfile -` → `/var/log/bip-api/access.log` + `ExecStartPre=+/usr/bin/install -d` for dir creation + new `infra/bip-api.logrotate` (14-day retention, copytruncate, compress). C3 = PGPASSWORD comment cleanup REJECTED on review (accurate documentation, not unused code). **Mid-sprint: Vivek made the GitHub repo public** to unblock VM `git pull` (private repo had no cached creds; previous deploys worked through expired temp cache). **Workflow gap surfaced:** `infra/deploy.sh` doesn't auto-sync `bip-api.service` to systemd — required manual `sudo cp + daemon-reload` after Stream C2's service unit changes. Filed as Sprint 88 candidate. Production smoke verified all changes live: Next 16.2.4 frontend, FastAPI 0.124 backend, CORS tightened allowlist, `/var/log/bip-api/access.log` writing. Closeout: `specs/sprint-87-closeout.md`.

2026-05-02 (Claude): Sprint 86 closed. **First sprint operating under the Deferral Policy.** 5 streams shipped end-to-end + 1 legitimately deferred Award calibration item (data-blocked). 490 → 500 backend tests, `npm run build` clean, `npm run lint` 0 errors. Streams: A = bracket label richness + backfill script (parent_*_seed/team_abbrs surfaced; 4 new PlayoffSeriesResponse fields; idempotent `data/backfill_playoff_parent_pointers.py`); B = sortable column headers on SeriesPlayerLogTable (8 stat columns, click-to-toggle direction); C = team-level tracking + hustle full stack from scratch (Alembic 0022 with new tables + ORM models + 12-call multi-measure nba_client wrapper + sync functions + services + endpoints + 2 frontend panels mounted in team analytics tab); D = OG image polish (route.tsx 190→770 LOC, 5 per-type renderers via `?type=player|team|series|mvp`, custom fonts via `tryReadFontAnyExt`, sibling layout.tsx for client-component pages); E = doc-only (broadened Cloudflare cache rule 4 regex for daily-synced player+team endpoints, dropped Spotrac retry from BACKLOG after 7-day prod log scan returned 0 matches, applied Why-deferred annotation to Award calibration). Phase 6 surfaced 1 fix: schema test pinned to Sprint 85 alembic head; bumped to `0022_sprint86_team_track_hus`. Production smoke verified all 5 surfaces live (bracket has 6 parent fields, /api/teams/OKC/tracking 200, /api/teams/OKC/hustle 200, /og 200 image/png, /og?type=player 200 image/png). Backfill ran in production: `closed_seen: 2, updated: 0, skipped_child_missing: 2` — correct behavior, R2 child rows will be created on next nightly bracket sync at which point parent pointers populate via Sprint 85's auto-advance close-transition. **Workflow lessons:** Deferral Policy + Phase 1 scoping rule prevented the natural "60% MVP" trap; subagent "stages, parent commits + verifies" is now standard SOP (3rd sprint with sandbox issue, fully formalized in stream prompts up front); 5-stream sprint shape works (small streams in main session + big streams via subagents); zero merge conflicts vs Sprint 85's 3 (lock-table claims + append-only discipline). Closeout: `specs/sprint-86-closeout.md`.

2026-05-02 (Claude): Sprint 85 closed. First sprint executed end-to-end under the new 8-phase workflow. **4 parallel streams** with subagents for A/B/C and main session for D + integration: D = lint cleanup (4 errors + 8 warnings → 0) + Monte Carlo flake fix (`hash(series_id)` → `series_id` directly; 10/10 stable); A = bracket auto-advancement with new Alembic 0021 (parent_top/bottom_series_id columns + NOT NULL relaxation, defensive `_has_table` guard for SQLite legacy-baseline path) + `_compute_next_round_slot` + `_auto_advance_closed_series` in `playoff_bracket_service.py` + `SeriesCard` TBD-pill rendering; B = new `/playoff-series/[seriesId]` route + `playoff_series_player_logs_service.py` + `GET /api/playoffs/series/{id}/player-logs` + `SeriesPlayerLogTable` component (grouped by player, links to `/games/{id}`); C = `player_tracking_service.py` + `player_hustle_service.py` + `/api/players/{id}/tracking` + `/api/players/{id}/hustle` + `PlayerTrackingPanel` (3 family toggle) + `PlayerHustlePanel` (single 8-tile grid) mounted in `PlayerDashboard`. Verification: 480 → 490 backend tests (+10 net new), `npm run build` clean, `npm run lint` 0 errors / 0 warnings (down from 4 errors + 8 warnings). **Phase 6 surfaced two latent infra bugs from Sprint 82+84:** (1) `infra/deploy.sh:21` `source /etc/bip/env` didn't auto-export vars to subprocesses → fixed with `set -a/+a`; (2) raw `python -m alembic` ignored DATABASE_URL because `alembic.ini` hardcoded a passwordless URL → fixed by invoking `python -m db.migrations` instead. Production smoke test: all 4 surfaces verified live (bracket has new parent fields; series player-logs returns 15+15 players; tracking returns 3 families; hustle returns stats). **Workflow lessons:** subagent sandbox issue (3rd sprint in a row) — formalized "subagent stages, parent commits + verifies" model in stream prompts up front; lock-table claims worked but the actual append-only discipline matters more than the lock; merge order D→A→B→C produced exactly 3 conflicts (test file section divider + 2 append-tail conflicts on api.ts/types.ts) all trivially resolved. Closeout: `specs/sprint-85-closeout.md`.

2026-05-02 (Claude): Sprint 84 closed. Two-stage sprint executed in one session. **Stage 1 — VM deploy:** Recovered SSH access to `5.78.114.15` via Hetzner rescue mode (mounted `/dev/sda1`, chrooted, created the missing `ubuntu` user with UID 1000 + sudo group + NOPASSWD, fixed home directory ownership, enabled `ssh.service` symlink — root cause of why SSH was refusing connections after our earlier disk write was that the rescue OS leaves `/mnt` empty by default and we wrote to the rescue tmpfs the first time). Configured Hetzner firewall (TCP 80/443 open). Registered `courtvue.app` via Cloudflare (`.app` not `.com` because `.com` was taken) and added 3 DNS records (api A → VM, @ + www CNAME → Vercel, all orange-cloud proxied). Ran `infra/caddy-install.sh` on the VM, set `/etc/bip/env` (NBA_API_USER_FETCH_DISABLED=true, CORS_ORIGINS, DATABASE_URL with new password for the `bip` Postgres user), installed gunicorn, ran `alembic upgrade head`, started `bip-api` + reloaded `caddy`. Caddy obtained Let's Encrypt cert for `api.courtvue.app` automatically. Imported repo into Vercel with `frontend/` root + `NEXT_PUBLIC_API_URL=https://api.courtvue.app`. First Vercel build failed on `useSearchParams` outside Suspense in `/bracket`, `/games/[gameId]`, `/teams/[abbr]` — fixed by wrapping each page's body in `<Suspense>` and shipped as `43b7a4a` on master. Configured Cloudflare cache rules (5 rules, TTLs 2hr-12hr matching the daily sync cadence) + WAF rule blocking empty user-agent + zgrab + masscan. End-to-end smoke: frontend 200, API health 200, leaderboards 200 with real data. **Stage 2 — workflow reset:** rewrote AGENTS.md (this file) and CLAUDE.md to reflect production-aware sprint structure. Added 8-phase Sprint Workflow (the QA / Pre-merge / Deploy / Smoke phases are new), Pre-merge Verification Checklist, Production Deploy Procedure, Rollback Procedures (frontend Vercel one-click, backend git checkout + deploy.sh, alembic downgrade -1, Cloudflare purge). Updated Session Start Checklist with mandatory production health check. Closeout: `specs/sprint-84-closeout.md`. **Workflow lesson:** the rescue-mode disk recovery wasted ~30 min because we didn't mount `/dev/sda1` to `/mnt` before writing — wrote to the rescue tmpfs, which vanished on reboot. Documented the chroot pattern in the closeout for future VM recoveries.

2026-04-28 (Claude): Sprint 77 closed on `feature/sprint-77a-game-data-foundation` + `feature/sprint-77b-broadsheet-screens` and merged to `master`. Two-team parallel sprint shipping the broadsheet/newsprint Playoff Home (replaces Sprint 73's carousel + slate during the playoff window) and the Game Detail deep-dive page with 12 new modules above the existing box-score sections. Stream A: new `services/game_trajectory_service.py` (WP trajectory + lead-tracker computed from PBP), `services/possession_diary_service.py` (24-row top-impact possession diary + per-quarter player +/-), `services/game_detail_assembler.py` (single resilient entry point for /api/games/{id}), `services/playoff_simulator_service.py` extended with `compute_series_odds_history`, `services/playoff_leaders_service.py` (new /api/playoffs/leaders endpoint with trend symbols + 5-game grades), `services/playoff_bracket_service.py` extended with `compute_game_storyline` (headline_storyline on /api/playoffs/today), and a new `frontend/src/hooks/useViewMode.ts` (auto-detect via useSeasonPhase + localStorage override). Stream B: new `frontend/src/components/broadsheet/` (11 components: BroadsheetMasthead, ModeToggle, BroadsheetHero, TodaysSlate, BroadsheetGameCard, SeriesTrackerStrip, BracketStrip, NarrativeLeaders, StoryRail, ArchiveVault, TipOffAgenda) and `frontend/src/components/broadsheet/game-detail/` (15 components including BroadsheetGameDetail, ScoreboardChrome, GameVariantToggle, plus the 12 page-modules — WP hero, lead tracker, dual shot charts, lineup grid, player impact cards, possession diary, coaching log, hustle stats, series odds card, quote ribbon). Auto-pick scoreboard for live/halftime, broadsheet for final + pre-game, manual toggle persists in localStorage. All broadsheet UI gated by useViewMode so toggle-back to regular_season or offseason renders existing Sprint 73 home cleanly. Architect → 8 parallel Engineers → Reviewer → Optimizer per CLAUDE.md. Reviewer signed off no-blockers; Optimizer addressed 3 cheap concerns (live-state inference tightened, LeadTracker + PossessionDiary memoized, WCAG AA contrast fix on impact tags). Verification: 360 backend tests (was 346, +14 new), `npm run build` + `npm run lint` clean (7 pre-existing warnings unchanged). Closeout: `specs/sprint-77-closeout.md`.

2026-04-28 (Claude): Sprint 76 closed on `claude/improve-evaluation-methods-ZAo94` and merged to `master`. Pure backend methodology rigor pass: shipped 8 reliability primitives, bumped 7 methodology versions end-to-end with structured response evidence (similarity_v3 shrunk Mahalanobis, custom_metric_v2 collinearity + weight sensitivity, scouting_brief_v2 contradiction detection, mvp_case_v4 Basketball Value sensitivity, style_xray_v2 PCA latent space, trend_intelligence_v2 Bayesian change scores, archetype_rules_v2 soft memberships), expanded the validation harness from 6 to 17 fixtures covering every registered methodology domain, and authored a design memo (`specs/methodology-future-modeling.md`) for the two remaining items (mvp_case_v5 voter calibration, opportunity_v2 uplift modeling) — both blocked on data prerequisites, not engineering. No frontend code changed; every new response field is `Optional`. Verification: 346 backend tests (was 293 at Sprint 75 close; +53 new), `npm run lint` clean (7 pre-existing warnings), `npm run build` clean. Closeout: `specs/sprint-76-closeout.md`.

2026-04-28 (Codex): Sprint 75 closed on `codex-sprint-75-playoff-command-center` and merged to `master`. Shipped Playoff Command Center on `/bracket`, `playoff_series_intelligence_v1`, `/api/playoffs/series/{series_id}/intelligence`, non-mutating simulator overrides, real SeriesWPSimulator what-if buttons, new `playoffs` methodology registry/docs, and targeted playoff tests. Verification: 293 backend tests, `npm run lint`, `npm run build`, `git diff --check`. Closeout: `specs/sprint-75-closeout.md`.

2026-04-28 (Codex): Sprint 74 closed on `codex-sprint-74-methodology-upgrades` and merged to `master`. Shipped `methodology_registry_v2`, methodology validation fixtures + `/api/methodology/validation`, shared frontend methodology metadata/types/API/hooks + `<MethodologyEvidenceCard>`, Shot Lab `shot_quality_v2` with hierarchical baselines + empirical Bayes stabilized shot-making + uncertainty/sustainability labels, and Team-Fit `team_fit_v3` with theoretical usage, fit-gap interpretation, reliability-gated better-fit labels, analysis-context warnings, and playoff low-sample notes. Wired methodology evidence across Team-Fit, Shot Intelligence, Opportunity, Archetype/Similarity, Trend/Trajectory, Style X-Ray, MVP/Gravity, Scouting Brief, and Custom Metrics. Verification: 290 backend tests, `npm run lint`, `npm run build`, `git diff --check`. Closeout: `specs/sprint-74-closeout.md`.

2026-04-28 (Claude): Sprint 73 closed on `feature/sprint-73a-playoffs-data` + `feature/sprint-73b-playoffs-features` and merged to `master`. Playoffs Platform sprint: two-team parallel (Stream A data foundation, Stream B frontend playoff features). Stream A: Alembic 0012_playoffs_data_layer adds `playoff_series` table + `is_playoff` on `lineup_stats` + `season_type`/`series_id`/`series_game_num`/`playoff_seed` on `game_logs`/warehouse games; `nba_client` + `sync_service` + `daily_sync.sh` get `season_type` pass-through, a 2h `PLAYOFF_CACHE_TTL` during the playoff window, and a new `--post-game` cron path; `services/season_phase_service.get_current_phase()` auto-detects from date+data; `services/playoff_bracket_service` + `playoff_simulator_service`; new routes `/api/season-phase`, `/api/playoffs/bracket|series/{id}|today|series-simulation/{id}`; existing `archetype/team_fit/lineup_context/similarity` services accept `season_type`. Stream B: new `/bracket` route + `<PlayoffBracketView>` + `<SeriesCard>` + `useSeasonPhase` SWR hook; series-mode Pre-Read pivot with `<CoachingAdjustmentsTimeline>` (finally surfaces `data.adjustments` deferred from Sprint 72) + `<SeriesWPChart>`; home shift with `<DailyPlayoffSlate>` + `<SeriesNarrative>` carousel; leaderboards Regular/Playoffs toggle; `<SeriesWPSimulator>` on MVP; `<PostseasonHeatmap>` on leaderboards; `<OpponentLineupMatchupMatrix>` tab on team detail. Every playoff surface gates via `useSeasonPhase()` so the platform reverts cleanly outside the playoff window. Verification: 286 backend tests (was 266, +20 new), `npm run build` + `npm run lint` clean (7 pre-existing warnings). Architect → 8 parallel Engineers → Reviewer → Optimizer. Closeout: `specs/sprint-73-closeout.md`.

2026-04-28 (Claude): Sprint 72 closed on `feature/sprint-72-design-system-closeout` and merged to `master`. Design System Closeout + Visual Polish sprint: shipped every Sprint 70 backlog item plus the API payload audit's top 5 free UI wins plus a basketball polish pass. Stream A (design follow-ons): home league-leaders TREND sparkline column with new `/api/leaderboards/{stat}/trends` endpoint + `<Sparkline>` SVG primitive, Compare PlayerCard hardwood headers with color-coded names, MVP candidate-card hardwood + ★#1 chrome (richness preserved per user decision), `/learn/design-system` showcase page consolidating all Sprint 70+72 primitives, Pre-Read print stylesheet for clean coach-handoff PDFs. Stream B (API audit): Pre-Read `prep_context.urgency` badge + `headline` callout, MVP `support_burden` "Teammate quality" sub-card, Player archetype `reason` tooltip, RoleFitCard `hint` discoverability icon. Stream C: FloatingBall polish (specular shine, varied seam weights, two-layer shadow, four-stop fill). Architecture used Architect → 4 parallel Engineers → Reviewer → Optimizer per CLAUDE.md sprint process. Verification: 266 backend tests (was 263, +3 sparkline), `npm run build` + `npm run lint` clean (7 pre-existing warnings). Closeout: `specs/sprint-72-closeout.md`.

2026-04-28 (Codex): Sprint 71 closed on `codex-sprint-71-methodology-rigor` and merged to `master`. Shipped methodology registry endpoints, shared reliability primitives, optional `analysis_metadata` on Shot Lab/Team-Fit/Opportunity, platform methodology updates, and `specs/methodology-validation.md`. Backend-only/docs-only by design because Claude had independent frontend work in flight. Verification: 263 backend tests, `git diff --check`, methodology coverage checks, FastAPI import smoke. Closeout: `specs/sprint-71-closeout.md`.

2026-04-27 (Claude): Sprint 70 closed on `feature/sprint-70-design-system-integration` and merged to `master`. Design System Integration sprint: shipped Teams directory two-column redesign with conference filter and team detail preview, Metrics hero leader card with HeroHardwood texture (#1 ranked player, 72pt composite score), Pre-Read visual matchup header card with 6 bilateral MatchupBar comparison bars and a "Three things to win" Focus Levers section that surfaces previously-unrendered `data.focus_levers` from the API, and Compare deltas/takeaways panels (5 stat-delta cards + 3 plain-language bullets). Pure-frontend sprint with no backend changes; backend test count unchanged at 257 passing. Frontend `npm run build` and `npm run lint` clean (7 pre-existing warnings). Subagent rate-limit hit forced inline implementation — see closeout for the workflow lesson. Closeout: `specs/sprint-70-closeout.md`.

2026-04-27 (Codex): Sprint 69 implementation complete on `codex-sprint-69-team-fit-intelligence`. Shipped Team-Fit v2 explainability, `/api/team-fit/{player_id}`, Team-Fit similarity context pills, player analysis contexts with manual settings, automatic injury/recovery context from `player_injuries`, and injury-aware Trend Intelligence. Verification: 257 backend tests passing, `npm run build`, `npm run lint`, `git diff --check`, local Alembic migration `0011_player_analysis_contexts`; local backend/frontend servers killed and ports 8000/3000 confirmed clear. Closeout: `specs/sprint-69-closeout.md`.

2026-04-25 (Claude): Sprint 68 closeout on `feature/sprint-68-decision-intelligence-followups`. Closed all five Sprint-67 deferrals on one branch in one session: Opportunity `usg_pct` precision, Team-Fit similarity mode (with teammate-duplicate penalty), Scouting Brief deep-link banners (`source=brief`), coaching copy polish across 12 diagnosis tags + 5 brief cards, and the Player Archetype Evolution Timeline (new `/api/archetype/{id}/history` endpoint + `<ArchetypeEvolutionTimeline>` component). 4 new backend tests; full suite 247 passing. Closeout: `specs/sprint-68-closeout.md`.

2026-04-24 (Claude): Sprint 67 closeout on `feature/sprint-67-decision-intelligence`. Shipped the 15-archetype Player Archetype Engine, role-aware similarity (season + age modes), 12-tag Shot Profile Diagnosis, and the 5-card Scouting Brief. Three spec tune passes before code caught two routing bugs and one coverage gap; live-DB smoke caught two more bugs before merge. 47 new backend tests (243 passing). Closeout: `specs/sprint-67-closeout.md`. Cleaned up four untracked Sprint-65 leftover files that were silently breaking `npm run build`.
