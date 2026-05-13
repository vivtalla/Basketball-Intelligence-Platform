# Product Backlog

Future-only backlog for CourtVue Labs.

Use this file for:
- ideas that should survive beyond a single sprint closeout
- product opportunities that are promising but not yet scheduled
- internal platform work that matters enough to stay visible

Guidelines:
- keep entries product-facing and concrete
- explain why the idea matters
- sketch the likely shape without turning it into a full sprint spec
- keep shipped work out unless it becomes a clear follow-on opportunity

---

## Sprint 99 Candidates

### Cron env-propagation root cause — analyze the one-week capture (Sprint 98 A6 follow-on)
Why it matters:
Sprint 98 A6 added `env > /var/log/bip-cron-env/run-*.env` at the top of `daily_sync.sh`. After ~1 week of captures, run `backend/scripts/analyze_cron_env.py /var/log/bip-cron-env` to diff "had DATABASE_URL" vs "needed fallback" runs. The Sprint 97 self-source is the safety net but we owe ourselves the root cause.

Likely shape:
- ssh to the VM, run the analyzer, capture stdout
- If the delta is a known shell var (SHELL, PATH, PAM-related), file a fix at the cron/crontab level + document
- Once verified, `touch /etc/bip/no-env-capture` to stop the captures; clean up `/var/log/bip-cron-env/`
- ~30-60 min including a tidy-up commit

### Frontend `metric_as_of` chip on MvpRacePanel + ExternalMetricsPanel (Sprint 98 B3 follow-on)
Why it matters:
Sprint 98's backend ships `metric_as_of` on `LeaderboardEntry` and the `services/external_metric_staleness.py` helpers, but the two highest-visibility consumers (MvpRacePanel, ExternalMetricsPanel) don't render the chip because their data sources (`MvpAdvancedProfile`, `SeasonStats`) don't currently carry `external_metrics_meta`. Without the chip, a user looking at an EPM ranking from 4-week-old data has no way to know it's stale.

Likely shape:
- Thread `metric_staleness: Optional[Dict[str, MetricStaleness]]` through `MvpAdvancedProfile` and `SeasonStats` response models (additive, optional).
- Backend: populate it in the MVP service + the player-profile assembler. Use `staleness_snapshot()` from the existing helper.
- Frontend: add a small chip component (amber tint when >21d) and wire into MvpRacePanel candidate cards + ExternalMetricsPanel table rows.
- ~4-6 hr.

### D3 deep service tests for the 10 highest-risk untested services (Sprint 98 D follow-on)
Why it matters:
Sprint 98 D shipped the floor (shared `conftest.py` + 12 smoke tests + GitHub Actions CI). The ceiling — deep tests for the 10 services with the most blast radius — was deferred as "different domain — incremental." Pick the riskiest 3-5 each sprint going forward until done.

Start with:
- `sync_service.py` — mutates DB on every cron tick
- `playoff_bracket_service.py` — recently patched (Sprint 97), pin the patched behavior
- `pbp_sync_service.py` — PBP ingest, biggest data
- `advanced_metrics.py` — computed metrics, easy to silently regress
- `warehouse_service.py` — orchestration heart of the sync pipeline

Likely shape:
- 3-5 tests per service, focused on idempotency + error paths + edge cases
- Use the conftest fixtures (`test_db_session`, `seed_basic`)
- ~6-10 hr for 5 services depending on edge cases

### Ruff baseline cleanup + flip CI to blocking (Sprint 98 D follow-on)
Why it matters:
Sprint 98 D wired ruff into CI but kept it informational (`continue-on-error: true`) because the existing codebase has 73 baseline issues. The grace period was meant for one week. Once cleaned up, flip the workflow step to blocking.

Likely shape:
- `ruff check . --fix` for the 55 auto-fixable
- Manual review of the 15 unsafe-fixes + the 3 unresolved
- Update `.github/workflows/ci.yml`: drop `continue-on-error` on the ruff step
- ~2-3 hr.

### Cloudflare cache bypass on `/api/admin/*` (Sprint 98 B/C follow-on)
Why it matters:
Sprint 98 B added `/api/admin/playoff-series-drift` and C added 8 admin-key gated mutation endpoints. Cache rule 5 (catch-all 2hr TTL) currently caches their responses, including 403s for unauthenticated requests. Since admin clients are rare, the pollution is small, but it's still cleaner to bypass.

Likely shape:
- Cloudflare dashboard → cache rules → expand rule 1 (bypass-cache) to include `URI starts_with /api/admin/`
- Document the change in `infra/README.md`
- ~5 min UI work.

### Collapse dual R2-series-creation paths (Sprint 97 follow-on)
Why it matters:
`_auto_advance_closed_series` creates placeholder R2 rows with positional IDs (`YYYY-CONF-R2-TOP|BOT`); the build-from-games loop creates team-pair IDs (`YYYY-CONF-R2-TEAM-TEAM`). They were intended to converge as seeds get filled in, but in practice they diverge when conference arms aren't seed-symmetric, creating duplicate rows. Sprint 97's sibling-fallback patch prevents the duplicates but the underlying design smell remains.

Likely shape:
- Pick one canonical scheme — recommend team-pair IDs derived from game data, which is what the production state has converged to.
- Update `_compute_next_round_slot` to return team-pair IDs (requires the closed parent's winner team_id, which is available).
- Drop the placeholder-slot logic + sibling-fallback patch.
- Migration: rewrite any historical positional-ID series_ids on a one-time pass; ensure foreign-key consistency (no game_logs reference them after Sprint 97 cleanup).
- ~4-6 hr.

### Graduate first `/beta/*` page back to root (Sprint 96 follow-on)
Why it matters:
Sprint 96 moved 19 routes under `/beta/` with the explicit promise that pages graduate to root one at a time as each gets a focused rework. Pick the first candidate (likely `/beta/lineups` since it's the freshest from Sprint 95, or `/beta/teams` since it's high-traffic and central to the platform).

Likely shape:
- Pick the page with Vivek
- Rework UI/UX to "complete" standard
- `git mv frontend/src/app/beta/<page>` back to `frontend/src/app/<page>`
- Drop the redirect entry from `next.config.ts`
- Restore the primary nav link in `NavLinks.tsx`; remove from Beta dropdown
- Add to the keep-list documented in Sprint 96 closeout

### Persist `PlayoffSeries.status = "active"` flip on first game played (Sprint 96 follow-on)
Why it matters:
Sprint 96 hotfix `b26f28a` derives `status="active"` in `_series_to_response` and the `/today` post-pass when stored status is `"scheduled"` but observed wins > 0. The right home for the fix is the post-game sync path (`_maybe_advance_clinched_series` or a sibling helper). Removing the runtime derivation eliminates a "the truth lives in two places" smell.

Likely shape:
- Add a helper in `services/playoff_bracket_service.py` that flips any `scheduled` series with games played to `active`. Idempotent.
- Call it from `daily_sync.sh --post-game` immediately after `build_or_refresh_bracket`.
- Drop the response-layer derivation from `routers/playoffs.py`. Keep tests.
- ~1-2 hr.

### Bundle analyzer audit pass (Sprint 96 follow-on)
Why it matters:
Sprint 96 wired `@next/bundle-analyzer` behind `ANALYZE=1` but the audit pass was not run as part of the sprint. Document baseline chunk sizes per route; identify the next 2-3 `next/dynamic` candidates (likely Three.js scenes, the Compare page, the heavy `mvp` and `insights` workspaces).

Likely shape:
- `ANALYZE=1 npm run build`
- Snapshot the per-route chunk sizes table into `specs/performance-baseline.md` (new doc).
- Pick 2-3 dynamic-import candidates and ship them in the same sprint.
- ~3-4 hr.

### Eliminate `PlayoffSeries.top_wins`/`bottom_wins` denormalized cache (Sprint 96 follow-on)
Why it matters:
The denormalized `PlayoffSeries.top_wins/bottom_wins` columns are only updated by the 6am daily sync, drift between updates, and are bypassed by every consumer (Sprint 90 + 91 + 96 all added "compute fresh from `GameLog`" paths). The drift exists nowhere productive — the canonical truth is `GameLog`. Either remove the columns entirely or drive them via a trigger on game-completion.

Likely shape:
- Pick: drop the columns + Alembic migration, OR add a trigger / SQLAlchemy event listener to keep them current on `GameLog` insert/update.
- Either is ~3-5 hr including migration testing on a snapshot.

### Salary + contract integration → trade-feasibility filtering (Sprint 89 D follow-on)
Why it matters:
Sprint 89's `/teams/[abbr]/roster-fit` league candidates ranks players by statistical fit only — the methodology drawer explicitly disclaims "no salary, no contract length, no free-agent status, no trade feasibility." A coach/GM looking at the candidate grid currently has to mentally filter the unrealistic acquisitions.

Likely shape:
- Source contract + cap-hit data from Spotrac (the existing `data/scrapers/` pattern from Sprint 82c) — ~3-4 hr scraper work, depending on Spotrac structure changes.
- New `player_contracts` table seeded nightly.
- `RosterFitPlayerEntry` extended with `current_cap_hit`, `years_remaining`, `free_agent_year`, `expiring`.
- Frontend filters: "free agents next summer", "trade-feasible within $X cap distance", "expiring contracts only".
- Per Deferral Policy: "different domain" — Sprint 89's stat-based fit is a coherent ship; trade feasibility is a sister feature.

### Shot location overlap (Sprint 89 D follow-on)
Why it matters:
Sprint 89 fit uses 13 box-score features (pts/reb/ast/stl/blk/tov/ts/usg/per/par3/ftr) but no shot-location signal. A guard who only shoots above-the-break 3s scores perfectly against a roster already loaded with above-the-break shooters — that's a real overlap the current model misses.

Likely shape:
- Compute per-team shot-zone profile (8 zones from the existing `play_by_play_events` data).
- Compute per-player shot-zone vector from `player_shot_charts`.
- Add a `shot_diet_overlap` component to the fit score (or surface it as a separate "spacing fit" signal that the user can optionally weight).
- ~6-8 hr including methodology decisions on weighting.

### Defensive scheme clustering (Sprint 89 D follow-on)
Why it matters:
Sprint 88 populated team tracking + hustle data in regular season. We can now cluster teams by defensive identity (switch-heavy / drop / ice / aggressive trap) using deflections + contested shots + tracking distance. A defender's fit score should reward scheme alignment.

Likely shape:
- New `services/team_defensive_archetype_service.py` clusters teams via k-means on the tracking + hustle vector.
- Per-player defensive vector (deflections rate, contested shots, screen assists, etc.) scored against each scheme cluster.
- New `defensive_scheme_fit` component or signal in roster-fit.
- Methodology calibration risk — needs validation that the clusters are coachable, not just statistical noise.

### Play-type compatibility via Synergy data (Sprint 89 D follow-on)
Why it matters:
Synergy play-type data (already imported per Sprint 82) has per-player frequencies for transition / isolation / P&R / post-up / spot-up / etc. Two players who are both 50% P&R-ball-handler create role conflict that 13 box-score features don't surface.

Likely shape:
- Per-player play-type frequency vector + PPP (already in DB).
- Per-team aggregated frequency vector (weighted by minutes).
- Score candidate's frequency vector against team's existing distribution (a high-frequency P&R ball handler scores poorly against a roster that already has 2 high-frequency P&R ball handlers).

### Server-component refactor of stable pages for true ISR (Sprint 88 D follow-on)
Why it matters:
Sprint 88 Stream D added `revalidate` exports to 6 stable pages (`/players/[id]`, `/teams/[abbr]`, `/leaderboards`, `/standings`, `/milestones`, `/mvp`) via direct page exports + sibling `layout.tsx` exports. Build registered the ISR settings, but production responses still return `cache-control: max-age=0, must-revalidate` with no `x-vercel-cache: HIT` after multiple requests. Root cause: the underlying pages are `"use client"` components — Vercel can cache the server-rendered HTML but the client shell has no data baked in (data fetches via SWR client-side on every browser request).

Likely shape (per page family — could be split across multiple sprints):
- Convert `players/[id]/page.tsx` to a server component that fetches player data server-side (`await fetch(\`\${API}/api/players/\${id}\`)`) and passes it as props to a thin client wrapper. Initial HTML includes the data; Vercel's edge can cache it for the `revalidate` window. Browser SWR can revalidate on focus from the seeded data.
- Same for `/teams/[abbr]`, `/leaderboards`, `/standings`, `/milestones`, `/mvp`.
- Each page family is a separate refactor unit (~2-3 hr each). Could be one big Sprint 90 (12-15 hr) or split.

### Cache-effectiveness measurement (Sprint 88 C1 follow-on)
Why it matters:
Sprint 88 instrumented `CacheManager` with hit/miss/expired counters but we have no baseline yet. After 24-48 hours of production traffic, we should see a snapshot via `/api/health/cache-stats` and use it to tune cache TTLs.

Likely shape:
- Wait 24-72 hours for counters to accumulate
- `curl -s https://api.courtvue.app/api/health/cache-stats`
- If hit rate < 50% on certain key prefixes: bump TTLs in `nba_client.py` for those keys
- One commit, ~30 min after data is collected.

### R2 backup lifecycle rule (Sprint 87 deferred — Cloudflare UI step)
**Why deferred:** Cloudflare R2 dashboard UI configuration step, not code. Per Deferral Policy "different domain". Click-by-click instructions live in `infra/README.md` ("Backup retention" section); ~5 min in the dashboard.

### ~~Cloudflare `/api/health` bypass-cache rule~~ — RESOLVED in Sprint 90 as not-needed
On Sprint 90 review, the rule is unnecessary: the catch-all 2hr cache TTL covers `/api/health`, and UptimeRobot reaches origin every 5 min for direct health probes. The README already implicitly said this; Sprint 90 made it explicit + removed this BACKLOG entry.

---

## Deferred — Data Acquisition Blocked

### Award calibration cohort expansion
**Why deferred:** Blocked on data we don't have yet. Requires sourcing historical NBA voting data back to 2008-09 (~80 ballot rows across 4 seasons + DPOY/MIP/6MOY ballots) before any code work. Per the Deferral Policy, this qualifies as "blocked on data we don't have yet."

**Sprint 90 update:** Sprint 90 wired the calibration through end-to-end and ran the production materialization. If the LOO-CV Spearman against the existing 13-season cohort fell short of 0.7, this entry is the unblocker — sourcing more seasons widens the fold count and gives the modifier vectors more signal to fit against. Check `/api/methodology/mvp` `runtime_calibration.cross_validated_spearman` to see whether this is still needed.

Why it matters:
Sprint 79 shipped the `mvp_case_v5` calibration code; Sprint 90 ran the materialization + wired live calibration through to MVP race responses. The seeded `award_voting` table has 57 rows across 13 seasons (2012-13 → 2024-25). If LOO-CV in production stays below 0.7, the next move is more historical data — calibration falls back to the Sprint 76 hand-tuned priors and `calibration_pending` stays `True` (honestly reported).

Data acquisition path (the unblocking work, NOT a sprint):
- Source: `https://www.basketball-reference.com/awards/awards_{year}.html` has voting tables back to 1980 (well before 2008-09)
- Option A: web-scrape using the existing `backend/data/scrapers/sportsreference_cbb.py` pattern (~3-4 hr to write a new scraper)
- Option B: manual CSV editing — 4 seasons × ~20 rows each = ~80 entries, ~2-3 hr of focused effort
- **Recommendation:** manual CSV editing as a one-shot task that doesn't need a sprint allocation. Vivek can do whenever motivated.

Once data is sourced, the implementation work is ~30 min (no code change, just data + re-materialization):
- extend `award_voting_seed.csv` backward to 2008-09 (+4 seasons, ~20 more rows) for a wider LOO-CV set
- add DPOY / MIP / 6MOY ballot rows — same code path, different `award_type` filter
- re-run `python data/materialize_award_modifiers.py` and the calibration cache invalidates on next request (24h TTL); fitted weights re-fit against the wider cohort
- iterate on the modifier proxies in `materialize_award_modifiers.py` (especially `_clutch_proxy` and `_signature_games_proxy`) as PBP-derived clutch + signature-game data becomes available for older seasons

---

## Now — Shot/Data Platform

### Canonical Event Completeness and Backfill
Why it matters:
Sprint 38 proved the platform needs a durable completeness contract, not another one-off field expansion. We now have explicit completeness reporting and richer shot/game context, but older rows still need systematic backfill and reconciliation before future features can assume the full payload is always present.

Likely shape:
- define the final medium-term payload CourtVue should preserve for shot charts, play analysis, and 3D reconstruction, including timing, event identity, action context, lineup/team state, and any other high-value upstream fields we are likely to need
- keep completeness metadata attached to product reads so the UI can tell the difference between “no data exists upstream,” “data exists but has not been enriched yet,” and “legacy row missing newly required fields”
- maintain repeatable backfill and validation workflows that upgrade older persisted rows whenever the canonical payload expands
- prefer payload completeness and durable storage contracts over piecemeal feature-specific additions, so future analysis surfaces can launch without another reactive persistence redesign

### Alias Backfill for Edge-Case Players
Why it matters:
Sprint 28 shipped the unresolved ops UI, but the underlying identity gaps (two-way players, recently traded players, inactive roster edge cases) still need targeted alias expansion to prevent future unresolved rows accumulating.

Likely shape:
- identify players who regularly generate unresolved rows and add manual alias entries
- add a targeted roster-refresh path to `sync_player_aliases` for two-way and recently moved players
- keep stub-player creation gated until roster truth is more authoritative

### Migration Adoption and Operational Discipline
Why it matters:
Sprint 43 moved the backend onto Alembic-backed migrations and removed runtime schema mutation from app startup, but the repo still needs a final discipline pass so future schema work never slips back toward ad hoc helpers or drift.

Likely shape:
- document and standardize the exact local/dev/prod migration workflow across README, runbooks, and any setup scripts that still assume `ensure_schema.py`
- remove any remaining legacy documentation or ops habits that imply startup-time DDL is acceptable
- add one or two small operational guardrails so future schema work follows migrations by default

### Legacy Compatibility Retirement
Why it matters:
Sprint 43 isolated modern warehouse-first runtime paths from historical compatibility mode more clearly, but legacy reads are still present for some older-season workflows. The next cleanup should be narrower and more deliberate instead of letting compatibility stay fuzzy.

Likely shape:
- audit which historical product surfaces still depend on legacy tables and decide which ones truly matter
- keep compatibility explicit where it is still needed, but retire dead branches and stale source labels where it is not
- continue surfacing honest readiness/runtime-policy metadata instead of mixing compatibility logic into modern paths

### Shot Lab Court Geometry Polish
Why it matters:
Sprint 61 shipped richer hover affordances, replay-example chips, Shot Intelligence Ops panel, and baseline materialization — retiring the two prior Shot-Lab-centric backlog entries. What remains is the unfinished court-silhouette polish the earlier backlog noted.

Likely shape:
- Finish the shared `ShotCourt` silhouette so the three-point shell, baseline, lane, and free-throw geometry unmistakably match a real half-court
- Keep tuning shot-frequency heatmaps so the hottest pockets pop on neutral backgrounds without making the whole surface feel heavy

### Replay Workflow Follow-Ons
Why it matters:
Sprints 40, 41, and 63 turned replay into a real workflow across Game Explorer, scouting, shot lab, trend cards, Style X-Ray, prep, and related coaching handoffs. The next gains come from making sequence review feel more analytical and more selective, not merely broader.

Likely shape:
- deepen the 3D scene choreography beyond the current short sequence view without losing the exact/derived/timeline trust model
- improve sequence ranking and matchup-specific evidence selection so replay launches feel more intentional when multiple recent candidates exist
- keep sharpening sequence summaries, labels, and analyst controls so replay feels like a coaching tool rather than only a visual drill-down

### Visualization Follow-Ons (Sprint 31 seeds)
Why it matters:
Sprint 31 shipped the visual renaissance layer. Remaining follow-ons extend it to comparison surfaces and add interactivity.

Likely shape:
- `PerformanceCalendar` side-by-side in `ComparisonView` so game rhythm can be compared directly
- Trend arrows on `HomeLeagueLeaders` require a `delta` field on `LeaderboardEntry` from backend
- Entrance animation polish: stagger fade-up on platform area cards, skeleton loaders shaped to match final layout

### Team Prep Queue Follow-Ons
Why it matters:
Sprints 42, 63, and 66 made the prep queue substantially more opponent-aware, replay-aware, and archival-ready. The next gains are less about basic save/reopen support and more about making packet archives easier to manage at staff scale.

Likely shape:
- add richer packet archive controls such as search, sort, season filters, and series/opponent grouping for staff prep libraries
- extend prep continuity into compare/export surfaces so a saved packet can become a fuller staff handoff
- continue tuning urgency and first-action summaries for local performance and edge-case matchups

### Team Shooting Split Workflow Expansion
Why it matters:
Sprints 62 and 63 shipped the canonical team shooting-splits foundation, team-page shooting dashboard, Style X-Ray shot-profile drivers, and deeper compare/prep/team-defense workflow use. The next gains come from tightening trust, expanding ops visibility, and improving how staff package those insights.

Likely shape:
- validate tricky official families such as assisted-shot semantics and expose honest trust notes when upstream meaning is ambiguous
- add stronger coverage-health and refresh visibility for the shooting-split families if they become a daily coaching dependency
- improve printable/shareable outputs for shot-profile matchup edges once the underlying trust framing is stable

---

## Now — Decision Intelligence

### Methodology Calibration and Second-Wave Model Upgrades
Why it matters:
Sprint 71 added the platform methodology registry, shared reliability primitives, response-level `analysis_metadata`, and validation docs. Sprint 74 made that pattern visible across major product surfaces and upgraded Shot Lab (`shot_quality_v2`) and Team-Fit (`team_fit_v3`). The next value is calibration: proving thresholds, priors, and labels against historical examples rather than leaving them as deterministic expert settings.

Likely shape:
- expand the Sprint 74 validation harness from qualitative golden fixtures into historical calibration reports, drift alerts, and expected false-positive/false-negative notes
- calibrate Shot Lab stabilization priors and sustainability labels by shot family, role, and season type while keeping raw actual/expected values visible
- upgrade Similarity, Trend/Trajectory, Opportunity, Style X-Ray, MVP/Award Case, Gravity, and Custom Metrics with the same reliability/uncertainty pattern now used by Shot Lab and Team-Fit
- require every new methodology version to update `specs/platform-methodology.md`, registry metadata, validation notes, and proxy limitation language

### Archetype Peer-Pool Composition Explainer
Why it matters:
Sprint 67 + 68 made the player archetype engine the reference point for role labels, similarity, and scouting-brief content. Borderline classifications (Lu Dort 2024-25 → `movement_shooter` rather than `switchable_stopper`) are honest but surprising. The methodology drawer documents the rules but not the *peer pool* — analysts can't tell why their player did or didn't qualify, or what features were sample-gated out.

Likely shape:
- Surface the per-season pool size and the subject's own pool-entry status inside the methodology drawer (e.g. "340 rotation players in 2024-25; subject included with 11/12 features after sample-gating fg3_pct_z").
- Optionally show the top peers from the same pool (already available via the season-mode similarity call) so analysts can audit the cohort their player was z-scored against.

### Brief Deep-Link Banners on `/insights`
Why it matters:
Sprint 68 wired `BriefSourceBanner` for the player-page `#archetype` and `#shot-lab` anchors. The Usage & Efficiency and Trajectory cards still link to `/insights` with `source=brief` in the query string, but the Insights page doesn't currently render an inbound banner there. Staff who follow those deep links land in the workspace cold.

Likely shape:
- Drop the same `<BriefSourceBanner>` pattern into the relevant Insights tab when `source=brief` is in the URL.
- Echo the originating card type ("From Scouting Brief · Usage & efficiency") and optionally pre-pin the player.

### Team-Fit Calibration and Context Expansion
Why it matters:
Sprint 69 turned Team-Fit into an auditable player-page surface with current-team value, teammate overlap, alternate-team ranking, and methodology v2 score components. Sprint 74 upgraded it to `team_fit_v3` with theoretical-usage separation, reliability-gated better-fit labels, context warnings, and golden fixtures. The next gains are calibration and deeper lineup context: analysts should trust that score movement behaves sensibly for stars, specialists, traded players, thin rosters, injury-affected seasons, and playoff samples.

Likely shape:
- turn the Sprint 74 golden fixtures into a visible pressure-test gallery for Tatum/BOS overlap, specialist shooters, defensive anchors, traded/TOT seasons, playoff samples, and bad-fit obvious cases
- tune component weighting and confidence notes against those examples without adding salary, trade-value, contract, or probability modeling
- calibrate reliability-gated better-fit thresholds with historical same-season roster examples rather than fixed expert tiers
- add lineup-role compatibility once adjusted lineup context is reliable enough to support fit interpretation

### Analysis Context Rollout
Why it matters:
Sprint 69 added persisted manual analysis contexts plus automatic injury/recovery windows from existing injury data, and Trend Intelligence now avoids blunt `losing_trust` conclusions during injury-affected windows. Sprint 74 threads injury/recovery/availability context into Team-Fit confidence notes. Other decision surfaces still need to understand those contexts so analysts get one coherent read across the platform.

Likely shape:
- apply context flags to archetype confidence, scouting brief copy, similarity interpretation, and MVP/opportunity notes without hiding raw stats
- add richer inline editing and review workflows for manual context windows on the player page
- add fixture coverage for injured-star seasons, recovery windows, availability management, and true non-injury role drops

---

## Now — Product Intelligence

### Counterfactual What-If Suggestions
Why it matters:
The directional scenario layer now includes replay evidence and source-aware compare continuity, but it still needs stronger calibration and richer matchup trust signals before it feels like a dependable coaching workflow.

Likely shape:
- improve the current bounded scenario engine with clearer confidence framing, stronger comparable-pattern outputs, and opponent-aware variants where support is strong
- sharpen the replay-evidence selection logic so scenario follow-through feels more matchup-specific and less generic when support exists
- keep every scenario directional, bounded, and fully explainable

### Style Intelligence Follow-Ons
Why it matters:
Sprints 60, 62, and 63 turned Style X-Ray into a real team-identity surface with archetypes, neighbors, movement, shot-profile drivers, drift context, and workflow bridges. What remains is calibrating that identity layer so it feels more trustworthy over longer windows and more specific in matchup use.

Likely shape:
- extend history beyond the current short-horizon view and add clearer stability/scatter framing for noisy teams
- improve style-confidence explanations so analysts can tell when a neighbor or drift story is strong enough for coaching use
- keep improving shot-profile-aware explanations so the x-ray feels like a coaching identity tool rather than a standalone data-science card

### Comparison Sandbox Follow-Ons
Why it matters:
The sandbox is stronger after Sprint 25 and Sprint 42, but it still needs better printing, sharing, and story-specific follow-through to become a true staff workflow.

Likely shape:
- improve printable and shareable compare outputs for teams, lineups, and styles
- surface prep-selected levers and decision rationale more explicitly when compare launches from prep tools, scouting, or scenarios
- deepen story labels with matchup-aware and trend-aware framing instead of season-only summaries

### Play-Type Scouting and Clip Workflow
Why it matters:
Sprints 65 and 66 turned play-type scouting into a real staff handoff workflow: confidence-ranked claims, opponent-specific anchors, compare continuity, and packet pinning into Pre-Read. What remains is making claim curation and export more powerful once staff use rises.

Likely shape:
- improve clip-list export formatting, multi-claim curation controls, and workflow continuity with compare and broader staff packets
- surface inference-confidence analogs on focus-levers, what-if scenarios, and decision-tool rotation suggestions so the trust model is consistent across coaching surfaces
- explore richer clip packaging once staff need printable or bulk-shareable evidence bundles beyond the current packet markdown path

---

## MVP Tracking

### MVP Award-Race Follow-Ons
Why it matters:
Sprints 48-56 turned the MVP tracker into a case platform with eligibility, opponent context, support burden, Gravity context, refined Basketball Value/Award Case scoring, weekly voter timeline, Voter Room case comparison, player embeds, MVP coverage ops, and a Team Impact lens. Sprint 76 added Basketball Value weight-perturbation sensitivity (`mvp_case_v4`). The next gains are voter calibration, richer official-data coverage, lineup-aware on/off explanations, and more historically faithful longitudinal modeling.

Likely shape:
- decide when persisted daily snapshots should become a visible daily timeline toggle alongside weekly reconstruction
- add true voter-points ballot simulation once the Voter Room case-comparison foundation is stable
- formalize production automation policy for daily MVP snapshot jobs
- add historical dated rows for impact, Gravity, clutch, opponent-adjusted context, and signature-game leverage so the timeline can evolve beyond game-log-only reconstruction
- broaden official play-type/tracking/hustle refresh coverage and improve coverage health explanations per candidate
- add lineup-with/without teammate context and dated on/off history so Team Impact explains why a candidate's team changes when he sits or plays

### MVP Award Case Voter Calibration — activate fitted weights (`mvp_case_v5` follow-on)
Why it matters:
Sprint 79 shipped `award_calibration_service.py` with the full coordinate-descent + LOO-CV harness, seeded `award_voting` with 57 ballot rows (13 seasons), and wired `CALIBRATED_AWARD_CASE_WEIGHTS` into `mvp_service.py`. However the calibration returns `calibration_pending=True` because the fitting step needs historical Basketball Value + modifier vectors materialized per candidate-season. The math, constraints, registry bump (`mvp_case_v4 → v5`), and tests all shipped; only the data-materializartion step remains.

Likely shape:
- retroactively run `mvp_service.py` scoring logic against past seasons (2012-13 through 2024-25) to produce one `(player_id, season, bv_score, modifier_vector[5])` row per ballot candidate
- call `calibrate_award_case_weights(db)` — it will find the `award_voting` rows + new vectors and return real fitted weights instead of `calibration_pending=True`
- extend `award_voting_seed.csv` to cover 2008-09 through 2011-12 (+4 seasons, ~20 more rows) to push LOO-CV fold count from 13 to 17 and strengthen Spearman stability
- add DPOY / MIP / 6MOY seeds and extend the calibration harness to those award types (same code path, different `award_type` filter)

### Gravity Calibration and Official Coverage
Why it matters:
Sprint 51 shipped DB-first Gravity contracts and CourtVue proxy Gravity, but the next step is proving the proxy against richer official tracking domains and official NBA Gravity rows when the source stabilizes.

Likely shape:
- add scheduled/backfill jobs for the new play-type, tracking, hustle, and gravity tables
- compare CourtVue proxy Gravity against official NBA Gravity wherever rows are available
- improve spacing-lift and off-ball components with teammate efficiency and lineup-with/without patterns
- keep Gravity as a capped context adjustment until validation shows it is stable enough for stronger scoring influence

---

## Next

### Decision-Tool Calibration and Opponent Context
Why it matters:
Sprint 42 turned the team decision tab into a real opponent-aware workspace, and Sprint 43 cleaned up the architecture and removed the live timeout regressions. The next gains are now about calibration and workflow sharpness rather than emergency responsiveness.

Likely shape:
- improve minute-redistribution logic, uncertainty wording, and opponent-style adjustments
- connect lineup suggestions more directly into replay and rotation review workflows
- expand matchup exploit flags without losing explainability

### Trend Intelligence Follow-Ons
Why it matters:
Sprint 59 turned Trend Cards into a team + player Trend Intelligence workspace with shared pins, foundation coverage notes, and replay-aware team cards. The next gain is making that story easier to share, archive, and extend into lineup-specific review.

Likely shape:
- add export/share formatting for selected team card + pinned player foundation context
- add lineup-level weekly cards where sample support is strong enough
- deepen card-level evidence summaries so replay and compare launches feel more specific than recent-game context
- add visual polish to pinned-player foundation cards, sparse-data states, and movement series

### Focus Levers Follow-Ons
Why it matters:
Sprint 42 made focus levers opponent-aware and workflow-connected, but the panel should still get more precise and more replay-aware over time.

Likely shape:
- improve impact labels from margin/possession heuristics toward cleaner confidence and game-swing framing
- add direct lever-to-replay follow-through when evidence is strong enough
- keep sharpening how focus levers align with matchup flags, compare, and decision tools so one coaching story survives across surfaces

### Opportunity Workspace Follow-Ons
Why it matters:
Sprint 65 closed out the core Opportunity follow-ons (TTL cache, compare-handoff peers, role-fit AST/TOV depth, directional-hint gating calibration, and the long-standing `UsageEfficiencyDashboard.tsx` → `OpportunityDashboard.tsx` rename). Sprint 71 added response-level reliability metadata for Opportunity. The remaining same-sprint gains are about expanding the peer model beyond same-team scope.

Likely shape:
- expand Compare handoff peer lookup to league-wide positional cohorts instead of only the currently-scoped team, so a same-team handoff on BOS can still surface league-wide G peers when that is the intent
- keep tuning directional hints and confidence labels against real roster cases
- lift `_position_bucket` out of `opportunity_service.py` into a shared helper and switch `trajectory_service` plus any future callers, so bucket rules cannot drift between surfaces

### Opportunity Uplift — held-out backtest + UI surface (`opportunity_v2` follow-on)
Why it matters:
Sprint 79 shipped `opportunity_v2`: 286 role-expansion observations materialized, KNN service wired, `OpportunityRow.uplift` sibling field live. The acceptance criteria included a held-out 2024-25 backtest (train on ≤2023-24 neighbors, predict 2024-25 ts_delta, target MAE ≤ 0.025) that was deferred because the observation set at 286 rows makes for a thin held-out cohort. Also, the frontend doesn't yet render the `uplift` field.

Likely shape:
- run the held-out backtest once 2025-26 mid-season data is available to add a full new training season and a cleaner hold-out set
- surface `uplift.mean_uplift` and the IQR band as a compact evidence card inside `<OpportunityRow>` (the backend already returns it)
- show `evidence_confidence` as a color-coded pill (high=green, medium=amber, low=gray) with neighbor count tooltip
- show top-3 named comparables (`uplift.top_comparables`) as expandable chips with from_season and ts_delta

### Pre-Read Deck Follow-Ons
Why it matters:
The browser deck is materially stronger after Sprints 27, 32, 63, and 66: named packets, scouting claim carry-through, packet library/history, share links, and markdown export now exist. The next gains are about deeper archive management and broader packet-aware follow-through.

Likely shape:
- add lineup-specific notes, compare launches, and game-film follow-through links that preserve packet context
- add richer archive management such as search, filtering, packet presets, and season-long staff reuse workflows

### Metrics Follow-Ons
Why it matters:
The metrics workspace is live, but it still needs stronger carryover and reuse to feel like a true analyst tool.

Likely shape:
- expand curated metric collections and public templates
- improve metric-to-compare and metric-to-player handoff
- explore whether saved state should stay URL-based or evolve toward richer reusable workspaces

### Ask Workspace Follow-Ons
Why it matters:
Sprint 46 introduced the first StatMuse-inspired CourtVue Ask workspace with deterministic player/team query interpretation. The next value comes from expanding the grammar and making answers launch richer existing workflows with less manual setup.

Likely shape:
- preload Player Stats, Standings, Teams, Compare, and Game Explorer with interpreted query state instead of only linking to the broad destination
- add date windows, opponent filters, playoffs, positions, and "in a game" leaderboards
- add small recent-form visuals for player game logs and team last-10 margin answers
- keep improving alias coverage through the metric registry before adding any optional LLM-assisted interpreter
- expose enough query confidence/debug context in development to tune parser behavior safely

### Player Stats Saved Views and Workflow Follow-Ons
Why it matters:
Sprint 44 substantially upgraded the Player Stats workspace with better hierarchy, spotlighting, mobile scan-ability, and URL-backed workspace state. The next gains are no longer basic polish; they are workflow and reuse improvements.

Likely shape:
- add named saved views or presets on top of the current URL-backed state model
- improve export or copy-ready sharing so filters and board context are easier to hand off in staff workflows
- keep refining dense-table ergonomics only where real workflow friction remains, instead of reopening general visual polish

### Untapped API Payload — second-tier wins (carry-over from Sprint 72 audit)
Why it matters:
Sprint 72 surfaced and shipped the top five free UI wins from the API payload audit (Pre-Read urgency badge + headline, MVP support_burden, archetype reason tooltip, opportunity hint discoverability). The audit also flagged a second tier of medium-priority untapped fields that have UI value but need a small design pass before they ship.

Likely shape:
- **`PreReadDeckResponse.prep_context.best_edge_label` + `best_edge_rationale`** — currently rendered as part of the prep_context blob; promoting them to a dedicated "Biggest edge" card adjacent to focus levers would give them more visual weight. ~15 min.
- **`MvpCandidate.impact_consensus`** — render as a metric-agreement pill on each candidate card showing how many of the multi-metric impact systems (EPM / LEBRON / RAPTOR / PIPM / DARKO) agree on this candidate's tier. Adds a "wisdom of metrics" overlay separate from the existing composite score.
- **`MvpCandidate.signature_games` carousel** — currently rendered inline as a small list inside the case panel. Promoting this to a clickable carousel that deep-links into Game Explorer would pair well with the "Key moments" UX direction.
- **`TrajectoryPlayerRow.key_stat_deltas` standalone view** — currently used only to drive the existing `DriverBar` decomposition. Surfacing the full delta dict as a "stat-by-stat YoY" mini chart could replace one of the current Trajectory cards.

(`PreReadDeckResponse.adjustments` was deferred from Sprint 72 and shipped via the Sprint 73 `<CoachingAdjustmentsTimeline>` on the Pre-Read series-mode pivot.)

### Sprint 73 follow-ons (Playoffs Platform)
Why it matters:
Sprint 73 shipped the Playoffs Platform with a season-phase auto-detect, bracket page, series Pre-Read pivot, home shift, MVP simulator, Postseason heatmap, and opponent lineup matchup tab. Sprint 75 upgraded `/bracket` into a Playoff Command Center with series intelligence and real simulator overrides. Remaining gains are now about deeper data fidelity, archiving, and live freshness.

Likely shape:
- **PostseasonHeatmap position-bucket coloring** — Sprint 75 added position buckets to Playoff Command Center star burden, but the standalone heatmap still needs `position` on `LeaderboardEntry`; frontend can then color dots by G/F/C bucket instead of TS-delta sign.
- **Playoff Command Center v2 calibration** — compare `playoff_series_intelligence_v1` tactical edges against historical series outcomes and staff review notes; tune sample gates, edge thresholds, and warnings without hiding raw playoff values.
- **Opponent lineup head-to-head net delta** — replace the standalone net rating delta in `<OpponentLineupMatchupMatrix>` with a true shared-possession net delta once a `lineup-matchups` endpoint exists. Currently the matrix shows each cell's standalone value, not the head-to-head edge between the two specific lineups.
- **Series snapshot system** mirroring Sprint 66's `pre_read_snapshots` for full series archives — staff packets that capture the full series state at a moment in time.
- **Live in-game playoff updates** — sub-minute freshness via WebSocket ingest. Out of scope this sprint; would unlock real-time bracket/WP movement during games.
- **Full visual bracket tree on mobile** — Sprint 75 made the Command Center mobile-first, but the old pure bracket-tree view still needs a dedicated compact mobile visualization if it returns as a secondary view.
- **`nba_client.py` lowercase-generic typing cleanup** — file uses `from __future__ import annotations` so `list[dict]` runtime subscripts are safe (stringified), but worth normalizing to `typing.Dict[]`/`List[]` in a sweep for consistency with the rest of the backend.
- **Print stylesheet for `/insights/trajectory` and `/insights/x-ray`** — Sprint 72 added Pre-Read print rules; carry the pattern across so coaches can print other surfaces too.
- **Playoff PBP-derived tables** — ~~`player_on_off`, `lineup_stats` with `is_playoff=True` not yet refreshed~~ **Shipped Sprint 79** (Stream B): `is_playoff` cascade, `_upsert_lineup` bug fix, `sync_pbp_for_playoffs_from_db()`, migration 0014 indexes, daily_sync.sh wiring.
- **`bulk_sync_service` season-type pass-through** — ~~hardcoded "Regular Season"~~ **Shipped Sprint 79**: `season_type` parameter added at lines 372, 424; `sync_type` disambiguated for unique-constraint safety.

### Frontend component-logic test infrastructure
Why it matters:
Sprint 72 added a hand-tuned `supportBurdenScore` heuristic in `MvpRacePanel.tsx` that classifies candidates into Strong support / Balanced / Heavy lift bands. There's no test for it because the repo has no frontend Jest/Vitest setup at all. Future heuristics, formatters, and reducers will accumulate the same coverage gap.

Likely shape:
- pick Vitest (Vite-native, plays well with Next.js 16 + TypeScript strict)
- target only logic-heavy modules first: `supportBurdenScore`, `pctileColor`, `winner`, `formatVal`, anything with branchy math
- skip component-render tests for now — they're slower to maintain and the build/lint already catches structural issues
- run via `npm test` from `frontend/`; wire into pre-commit if it becomes a friction point

### Sprint 77 follow-ons (Broadsheet game-detail completeness)
Why it matters:
Sprint 77 shipped the broadsheet Playoff Home + Game Detail deep-dive with 12 modules above the existing box-score sections. Five modules render as empty-states or placeholders for v1 because the underlying data isn't computable from current sources. Closing these turns the game-detail page from "skeleton with WP/Lead/Diary depth" into a fully fleshed analytical surface.

Likely shape:
- **Per-game team shot charts** — `<DualShotCharts>` is empty-state v1. The existing `<ShotChart>` is keyed on `player_id` only; needs new backend that returns per-game shot data per team (game_id + team_id filter on the existing shot_charts table).
- **Per-game lineup data** — `<LineupGrid>` shows season-level lineups with a "per-game lineup data not yet wired" caveat. Needs PBP-stint extraction per game (the on-court tracking from Sprint 77 EA2 has the substitution data needed).
- **Per-game Hustle stats** — `<HustleStats>` empty-state v1. NBA API doesn't expose per-game hustle. Either compute proxies from PBP (deflections via STL events, contested shots via blocks events, charges from foul events) or skip entirely.
- **Per-game Coaching Log** — `<CoachingLog>` empty-state v1. No current data source. Could auto-generate from lineup-substitution patterns + timeout events in PBP, or accept manual entry from coaches.
- **Story Rail CMS wiring** — `<StoryRail>` v1 hardcoded editorial copy. Backlog item to wire to a real content source (CMS or AI-generated).
- **Archive Vault API** — `<ArchiveVault>` v1 hardcoded historical Finals MVP + tag pills. Needs a real archive endpoint that knows last N seasons' Finals and key players.
- **Per-game Player Impact (EPM/RAPM/clutch)** — `<PlayerImpactCards>` shows +/- per quarter only. Per-game EPM/RAPM/clutch deferred (no current data source).
- **N+1 query consolidation in `game_detail_assembler`** — Optimizer flagged but didn't refactor mid-sprint. Each component service issues its own `db.query(PlayByPlay)` for the same `game_id`. Consolidation requires service-signature changes (pass pre-loaded events list rather than re-querying).
- **Live game state signal** — auto-pick currently infers from `home_score == null || away_score == null`. Backend should expose a canonical `is_complete` / `game_status` field on `GameDetailResponse` for cleaner detection (one-line backend change).

---

## Later

### Research Review Library
Why it matters:
CourtVue Labs can become more valuable if it helps users connect product workflows to the broader basketball research ecosystem.

Likely shape:
- summarize outside basketball research and link original articles or papers
- organize research by topic, method, and practical use
- make it a companion layer rather than a disconnected content archive

### NBA Draft Workspace
Why it matters:
Draft research is a natural adjacent expansion, but it is a separate product lane and should be treated deliberately.

Likely shape:
- add a draft page with NCAA men's data, prospect profiles, and mock-draft views
- support player cards, comparables, archetype tags, and draft-board style exploration
- keep draft work separate from current NBA workflow assumptions

### Court-Level Onboarding and Product Story
Why it matters:
As the product expands, it needs a clearer first-run experience and a stronger explanation of who it is for.

Likely shape:
- guide new users into player research, team prep, metrics, or coaching workflows
- sharpen home-page positioning and workspace explanations
- make CourtVue Labs feel like a coherent product, not just a collection of tools

### Workspace and Git Hygiene
Why it matters:
Internal cleanup is not user-facing, but it protects sprint velocity and reduces operational mistakes.

Likely shape:
- continue branch cleanup, remote cleanup, and worktree discipline
- keep AGENTS.md branch-maintenance policy current
- reduce stale branch risk and workspace confusion before each sprint kickoff

### Warehouse Visibility and Readiness UX
Why it matters:
Data reliability will remain a product feature, especially as decision-support surfaces get more ambitious.

Likely shape:
- improve worker visibility, backlog monitoring, and readiness messaging
- tighten runbooks around recovery and backfill operations
- help analysts understand when a workflow is fully trustworthy versus partially covered

### Shot Data Enrichment
Why it matters:
The current shot-chart storage supports today’s visuals, but deeper shot-quality analysis will need richer context than x/y, make/miss, and basic zone tags.

Likely shape:
- evaluate storing shot-level `game_id`, game date, period/clock, and richer context fields when upstream data supports it
- decide whether those enrichments should live in the existing JSON payload or a more structured summary table
- keep the first follow-on targeted to real product use cases instead of collecting fields speculatively

---

## Platform Gaps (deliberate scope boundaries — candidates for future phases)

### Tracking Data Integration
Why it matters:
Every CourtVue number today is derived from box scores, play-by-play, and shot-chart zone aggregates. Shot diagnosis tags like `elite_corner_gravity` and `rim_pressure_elite` are inferred from zone-level frequency + efficiency deltas, not from true defender-contest distance or positional tracking. Adding Second Spectrum or similar positional data would sharpen these signals materially and unlock new surfaces (off-ball movement, spacing maps, on-ball defense metrics).

Likely shape:
- define which tracking families matter most for existing surfaces (defender distance for shot quality, speed/distance for load monitoring, off-ball positioning for spacing)
- evaluate data availability and licensing before committing to a schema
- integrate incrementally: one tracking family per sprint, validate against existing zone-level proxies, keep proxies as fallback

### Draft / Prospect Workspace
Why it matters:
The archetype engine and similarity service already produce the right primitives for prospect evaluation, but they run on NBA `season_stats` only. Draft research is a natural product expansion that would let front-office users apply the same Decision Intelligence surface to incoming talent.

Likely shape:
- add NCAA men’s data ingestion alongside the existing `nba_api` pipeline
- run archetype classification and similarity against a mixed NBA + NCAA pool with era-normalization caveats
- keep draft work in a separate route namespace so it doesn’t pollute NBA-season assumptions
- see also the existing "NBA Draft Workspace" entry in the Later section

### Live / In-Game Data
Why it matters:
The pipeline is daily-sync only. There is no WebSocket feed, no in-game lineup tracking, and no real-time shot chart updating during a game. Coaching staff use cases (rotation tracking, live lineup net rating) require sub-minute data freshness that the current batch model cannot support.

Likely shape:
- evaluate a streaming ingest path (WebSocket or polling) for live game state — at minimum current lineup and score
- define which product surfaces benefit most from live data (lineup rotations, clutch situation flags, shot chart mid-game)
- keep the existing daily-sync pipeline as authoritative historical record; live data supplements, doesn’t replace

### User Accounts and Saved Workspaces
Why it matters:
Pre-read packets are assembled in-session and exported to markdown but not persisted server-side. There is no login, no saved player lists, no org-level sharing, and no persistent workspace beyond URL-backed filter state. Staff workflows at scale require at minimum named saved views and shared packet libraries.

Likely shape:
- define the minimum auth model (individual vs org-level, read-only sharing vs full edit)
- persist Pre-Read packets server-side with a packet library accessible across sessions (extends the Sprint 66 packet history work)
- add named saved views on top of the existing URL-backed Player Stats state
- keep the no-login path working for anonymous / single-user deploys

### Probabilistic / ML-Backed Models
Why it matters:
CourtVue intelligence is still primarily deterministic: z-score rules for archetypes, weighted Euclidean distance for similarity, arithmetic templates for scouting copy. Sprint 71 added the methodology registry, reliability primitives, and validation documentation needed to introduce more advanced models responsibly. Some signals (shot-making stabilization, role expansion, trend change detection, aging curve shape) are inherently probabilistic and would benefit from learned or Bayesian models.

Likely shape:
- identify 1–2 narrow, high-value prediction targets where a trained model meaningfully outperforms a heuristic (aging curve trajectory is the clearest candidate)
- keep deterministic rule engines as the default for all classification and diagnosis work — ML is additive, not a replacement
- gate any model output behind an explicit confidence + methodology disclosure so the product’s auditability brand is preserved
- require model cards, calibration notes, uncertainty bands, and explainable driver breakdowns before any probabilistic output becomes product-facing
