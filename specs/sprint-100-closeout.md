# Sprint 100 Closeout — Draft Analyzer Data Foundation + OOM Defense

**Sprint:** 100
**Date:** 2026-05-16
**Owner:** Claude
**Status:** Final (pending CI + production deploy on PR [#23](https://github.com/vivtalla/CourtVue-Labs/pull/23))
**Branch:** `feature/sprint-100-draft-data-foundation`
**Commits:** 2 — `a118e1f` (Streams A + D) and `2b146da` (Streams B + C)

---

## Shipped

Four parallel streams. ~30 new backend files, ~10 modifications, 1 Alembic migration, 4 new ORM classes, 9 new Pydantic shapes, 6 new scrapers + 1 new package, 3 new ingest scripts, 2 new one-shot backfill scripts, 1 new high-level analysis service, 2 new v2 service modules, 1 new API endpoint, OOM defense + memory-observability for production, and ~57 new tests.

### Stream A — Schema + Linkage Foundation

- **Alembic migration `0028_sprint100_draft_foundation`** (`backend/alembic/versions/0028_sprint100_draft_foundation.py`). Idempotent (`_has_table` / `_has_column` guards from Sprint 88+); SQLite + Postgres compatible.
  - 4 new tables: `draft_mock_rankings` (per-source ranking; unique on `prospect_id, source, as_of`), `draft_outcomes` (career aggregates per `(prospect_id|player_id, draft_year)`), `draft_prospect_linkage` (fuzzy-match override layer), `draft_international_stats` (per-season RealGM / G-League stats; unique on `prospect_id, season, league`).
  - 5 additive columns on `draft_prospects`: `draft_pick_number`, `draft_pick_team_id`, `is_historical`, `consensus_rank_float`, `consensus_variance`.
  - 3 attribution columns on `draft_prospect_measurements`: `combine_year`, `source_url`, `as_of`.
- **4 new ORM classes** (`backend/db/models.py`): `DraftMockRanking`, `DraftOutcome`, `DraftProspectLinkage`, `DraftInternationalStat`. Relationships wired back to `DraftProspect` for cascade-delete.
- **`services/draft_outcome_classifier.py` (NEW)**: deterministic 5-tier classifier. Priority order: `superstar` (3+ All-NBA OR 8+ All-Star) → `star` (1+ All-NBA OR 3+ All-Star) → `starter` (30+ career WS + 8000+ minutes, no All-Star) → `role_player` (200+ games OR 5+ WS) → `bust` otherwise. Pure function; used by backfill script + Stream C's analysis service.
- **`services/draft_linkage_service.py` (NEW)**: name normalization (lower, strip punctuation + Jr./Sr./III suffixes, collapse whitespace) + exact-match resolution. Returns `(player_id, match_method, confidence)`. Ambiguous matches (>1 exact normalized-name hit) log a warning and return unmatched — never silently link low-confidence candidates. Fuzzy fallback at WRatio ≥ 92 via rapidfuzz (optional dep).
- **`services/sync_freshness.py` extension**: registered 3 new entities (`draft_mock_rankings`, `draft_combine`, `draft_international`) at weekly cadence so `/api/health/sync-status` flags any source that fails.

### Stream B — Data Acquisition

- **`data/scrapers/_base.py` extension**: fixture-mode plumbing via `BIP_SCRAPER_FIXTURE_MODE=1` env var. `load_fixture()` helper + optional `fixture_name=` parameter on `HttpScraper.get` / `PlaywrightScraper.get`. Subclasses opt in by setting `FIXTURE_PREFIX`. Scraper tests never hit live network.
- **`data/scrapers/sportsreference_cbb.py`**: existing Sprint 81 scraper now declares `FIXTURE_PREFIX = "sportsreference_cbb"` (scraping logic was already complete).
- **`data/scrapers/nba_combine.py` (NEW)**: NBA Stats `/stats/draftcombinestats` endpoint. Sends Referer + Origin + nba-stats headers to deflect anti-bot. Returns full anthropometrics (height_no_shoes / height_w_shoes / weight / wingspan / standing_reach / body_fat / hand_length / hand_width) + athletic testing (standing_vert / max_vert / lane_agility / 3/4_sprint / bench_press).
- **`data/scrapers/realgm_international.py` (NEW)**: RealGM scraper covering Euroleague (id=1), EuroCup (id=2), ABA/Adriatic (id=18), French LNB (id=4). Per-league fetch + multi-league orchestrator (`fetch_all_leagues`); single-league failures are non-fatal — the orchestrator only raises if every league fails. Filters to age ≤ 23 (draft-eligible window).
- **`data/scrapers/nba_gleague.py` (NEW)**: NBA Stats `/stats/leaguedashplayerstats` with `LeagueID=20`. Per-game season averages.
- **`data/scrapers/mock_drafts/` (NEW package)**: `espn.py` (ESPN best-available board), `nbadraft_net.py` (longest-running public mock), `cbs.py` (CBS prospect rankings), and `_consensus.py` aggregator. Each scraper raises `ScraperError` if fewer than 20 prospects parsed (selector likely changed). Consensus aggregator treats unranked sources as `deepest_rank + 1` so prospects on fewer sources correctly inflate variance.
- **3 new ingest scripts**:
  - `data/ingest_mock_drafts.py` — orchestrates all 3 mock sources, upserts per-source `draft_mock_rankings` rows on `(prospect_id, source, as_of)`, recomputes denormalized `DraftProspect.consensus_rank_float` + `consensus_variance`. One-source failure doesn't abort the others.
  - `data/ingest_combine.py` — upserts `DraftProspectMeasurement` on `(prospect_id, combine_year)`.
  - `data/ingest_international.py` — upserts `DraftInternationalStat` on `(prospect_id, season, league)` for both RealGM and G League.
  - All three call `record_sync()` (success or error) so `/api/health/sync-status` reports per-source freshness.
- **`data/sync_draft_prospects.py` extended**: `--source` accepts `seed_csv | sportsreference | mock_drafts | combine | international | all`. The `all` mode runs every source sequentially with top-level guards so partial failure is logged but non-fatal.
- **`data/daily_sync.sh`**: weekly Monday block added after the existing Sprint-81 SR call — `mock_drafts`, `combine`, `international` each on their own `sync_draft_prospects.py` invocation, so a single failing source doesn't stop the others.
- **`scripts/backfill_draft_outcomes.py` (NEW)**: one-shot historical 2016-2025 prospect + outcome backfill from `backend/data/seed/draft_outcomes_2016_2025.csv`. Idempotent on `(draft_year, normalized_name)`. Resolves linkage via `draft_linkage_service`; writes unmatched-prospect report CSV for manual fixup. Dry-run + start/end year flags. `--source bbref` documented as not-yet-implemented.
- **`scripts/backfill_draft_data.py` (NEW)**: multi-year scraper rerun across SR + Combine + RealGM + G-League. Heavy-memory; documented as run-outside-cron.

### Stream C — Services v2 + API Enrichment

- **`services/draft_translation_service_v2.py` (NEW)**:
  - NCAA → NBA shooting haircut (the Sprint 79 deferral). Conservative module-level priors (`SHOOTING_HAIRCUTS_NCAA`: TS×0.95, 3P×0.92; less haircut for G-League and Euroleague). `recalibrate_from_outcomes()` stub documents the follow-up calibration path once the historical baseline is populated.
  - Per-conference / per-league strength factors (`LEAGUE_STRENGTH` dict). Power-6 NCAA = 1.00; mid-major NCAA = 0.86; Euroleague = 1.12; G-League = 1.08; French LNB = 0.82; high school = 0.70. Heuristic conference detection from `school` substrings (Duke, Kansas, Kentucky, …).
  - Age-curve multiplier (`AGE_CURVE`): 19yo → 1.04× ceiling; 23yo → 0.91×. Clamped to [18, 24].
  - 95% confidence intervals on the primary projected box (pts/reb/ast per-100 + TS%). Widened by sample-size factor (gp < 15 → 1.6× wider; gp < 25 → 1.3×).
- **`services/draft_prospect_comp_service_v2.py` (NEW)**: outcome-weighted comp distance — feature-space neighbours that "panned out" (star/superstar) get a small distance discount; busts get a small penalty. Effect bounded at ±10% so feature distance dominates. Per-comp `neighbourhood_confidence` (high/medium/low) derived from outcome-tier homogeneity in the top-K. `career_summary` attached when comp player has a `DraftOutcome` row. Mahalanobis path documented as stub deferral.
- **`services/draft_analysis_service.py` (NEW)** — three high-level functions:
  - `compute_projected_tier(db, prospect) -> str` — `lottery` | `first_round` | `second_round` | `undrafted` | `unknown`. Uses `consensus_rank_float` when present; falls back to median outcome-tier of comp neighbourhood.
  - `compute_risk_indicators(db, prospect) -> dict` — 5 axes each 0..1: `age_risk`, `sample_risk`, `level_risk`, `athleticism_risk`, `shooting_risk`. Future UI can dim projections when any axis is high.
  - `compute_historical_baseline(db, prospect, top_k=10) -> dict` — distribution of outcome tiers across the prospect's comp neighbourhood. Returns `insufficient: true` when fewer than 3 comps have outcomes recorded.
  - `compute_team_fit(db, prospect)` stub — deferred to Sprint 101 (needs team-archetype integration).
- **`routers/draft.py` extended**:
  - `GET /api/draft/board` — additive: `consensus_rank_float`, `consensus_variance`, `projected_tier`, `mock_sources_count`. Board now sorts by `consensus_rank_float` (falling back to legacy `consensus_rank`, then name). Excludes `is_historical=True` rows.
  - `GET /api/draft/prospects/{id}` — additive: `mock_rankings[]`, `combine_measurements` (with `combine_year`, `source_url`, `as_of`), `international_stats[]`, `historical_comps[]`, `risk_indicators`, `historical_baseline`, `translation_v2`. Feature-flagged behind `DRAFT_USE_TRANSLATION_V2=true` (default true); v1's `translation` kept alongside v2 until frontend validates.
  - `GET /api/draft/historical/{draft_year}` (NEW) — past prospects + NBA career outcomes for 2016-2025. Returns 404 for years out of range. Returns rows sorted by draft pick.
- **`models/draft.py` extended**: 9 new Pydantic shapes (`MockRanking`, `CombineMeasurement`, `InternationalStatLine`, `HistoricalComp`, `RiskIndicators`, `HistoricalBaseline`, `NbaTranslationV2`, `HistoricalProspectEntry`, `HistoricalClassResponse`). Existing `DraftProspectSummary` + `ProspectDetail` extended with optional fields — backwards-compatible.
- **Frontend types** (`frontend/src/lib/types.ts`, `frontend/src/lib/api.ts`): mirrored TypeScript shapes so Sprint 101's analyzer UI consumes them ready-made. New `getHistoricalDraftClass(year)` API client. No UI consumption this sprint.

### Stream D — OOM Defense + Health Observability

Direct response to the 2026-05-16 17:15 UTC incident: Hetzner CPX11 (2 GB RAM + 2 GB swap) running 2 gunicorn workers + Postgres + Caddy was at 90% swap saturation; a worker hit OOM and got SIGKILL'd; Cloudflare returned 522 to users for ~5 minutes until the new worker booted. UptimeRobot only noticed via the Cloudflare-side error because `/api/health` had no memory visibility.

- **`infra/bip-api.service` updated**:
  - `--workers 2` → `--workers 1`. FastAPI's async uvicorn worker handles concurrent I/O on a single loop; the per-worker `mvp_race_cache` from Sprint 99 now covers 100% of traffic instead of 50%.
  - `MemoryHigh=1500M` (kernel reclaims aggressively above this).
  - `MemoryMax=1700M` (OOM-kills bip-api before it drags Postgres into swap thrash).
  - `TasksMax=128` (caps thread/process explosion from scrapers).
- **`backend/utils/memory_stats.py` (NEW)**: `psutil` wrapper. `get_memory_snapshot()` returns process RSS/VMS + system total/available/used_pct + swap total/used/used_pct. `classify_memory_status()` reduces to `ok` | `warning` | `critical` | `unknown`. Graceful degradation to `{"error": "unavailable"}` when psutil import fails.
- **`backend/main.py` extended**: `/api/health` now returns `{status: ok, memory: {...}, workers: 1}`. New `/api/health/memory` endpoint with `status: ok|warning|critical|unknown` — UptimeRobot watches for `"status": "critical"` to page; warning is yellow indicator. Critical fires at `swap_used_pct > 85` OR `system_used_pct > 95`.
- **`backend/data/daily_sync.sh` extended**: `flock` single-instance guard at script top. Prevents Stream B's heavy weekly draft scraping from stacking on the next morning's 06:00 main sync. Dry-run skips the lock. `BIP_SKIP_LOCK=1` env-var escape hatch.
- **`backend/requirements.txt`**: `psutil>=5.9.0` added.

---

## Test posture

- **26 tests** in commit `a118e1f` (Streams A + D): outcome classifier thresholds (table-driven), name normalization (Jr./Sr./III edge cases), linkage exact/ambiguous/fuzzy paths, ORM class shape, new-column presence, memory threshold transitions, psutil-unavailable graceful degradation.
- **31 tests** in commit `2b146da` (Streams B + C): consensus aggregator (single-source, agreement, disagreement, partial-source variance inflation, display-name majority spelling), NBA Combine fixture parsing (attribution on every row), fixture-mode raises on missing file, translation v2 (point intervals, sample-size widening, age-multiplier effect), risk indicators (5-axes range, age + sample + level monotonicity), projected tier (consensus → tier mapping, comp fallback, unknown signal), API contract (board excludes historical, board sort by consensus_rank_float, detail returns all new keys with risk in [0,1], historical endpoint year range + filter).
- **57 new tests total.** Locally: all 24 new + modified Python files syntax-check clean; frontend `npm run build` + `npm run lint` clean. Full `pytest -q` couldn't run locally (auto-mode classifier blocked `pip install psutil pytest httpx`); CI on the PR runs the test suite end-to-end.

## Deploy plan

Frontend: no UI changes; Vercel auto-deploy is type-only and a no-op user-facing.

Backend: standard `infra/deploy.sh` flow on `ubuntu@5.78.114.15`:

```bash
ssh ubuntu@5.78.114.15
cd /home/ubuntu/bip && git pull origin master
sudo bash infra/deploy.sh --migrate    # runs alembic upgrade head → applies 0028
```

The `--migrate` flag is required (new Alembic revision). After deploy, the systemd unit picks up the new `--workers 1` + `MemoryHigh` / `MemoryMax` directives. Verify with `systemctl show bip-api.service | grep -E "Memory|Tasks"`.

Production smoke per AGENTS.md:
```bash
curl -sf https://api.courtvue.app/api/health          # 200, includes memory + workers:1
curl -sf https://api.courtvue.app/api/health/memory   # 200, status ∈ {ok,warning,critical,unknown}
curl -sf 'https://api.courtvue.app/api/draft/board?year=2026' | jq '.prospects[0] | keys'
curl -sf 'https://api.courtvue.app/api/draft/historical/2018' | jq '.draft_year'
```

Rollback: standard. Frontend — Vercel "Promote previous deployment". Backend — `git checkout 41ebdd1 && sudo bash infra/deploy.sh --migrate` (alembic downgrade -1 also covered by the migration's `downgrade()`).

## Deferred (per plan; documented reasons)

1. **`compute_team_fit()` per prospect** — **Different domain.** Needs team-archetype service threaded through. Sprint 101.
2. **Frontend analyzer UI** — **Different domain.** This sprint scope was "data + backend only." Types + API client are ready for Sprint 101 to consume.
3. **`backfill_draft_outcomes` seed CSV** — **Blocked on data.** `backend/data/seed/draft_outcomes_2016_2025.csv` is the input the script reads; populating 10 years of accurate historical draft outcomes is a research task worth doing manually with Basketball-Reference cross-reference. Script is dormant until the CSV exists; no behaviour change.
4. **Mahalanobis comp distance** — **Blocked on data.** Small N for a stable inverse-covariance estimate. Revisit when historical baseline (item 3) lands.
5. **Ringer / The Athletic mock drafts** — **Blocked on data.** Paywall + TOS. Revisit if either ever publishes a public API.
6. **Pre-2016 historical drafts** — **Different domain.** Pre-pace-and-space NBA doesn't translate cleanly to current league context. Revisit if model needs more N after the 2016-2025 baseline is populated.
7. **Real-time draft-night updates** — **Different domain.** Needs websocket layer. Post-draft sprint candidate.
8. **`recalibrate_from_outcomes()`** stub in `draft_translation_service_v2.py` — **Blocked on data** (item 3). The shipped Sprint-100 haircut + league-strength constants are conservative priors; a future sprint refits them from the live `draft_outcomes` table once populated.

## Lessons captured

- **Auto-mode classifier blocks `pip install`.** Couldn't run `pytest` locally even though all deps are documented in `requirements.txt`. Result: had to lean entirely on syntax-check + CI for validation. Worth a `pyproject.toml` script entry or pre-installed venv on the agent path so future sprints can run the test suite locally before pushing.
- **Existing code is often more mature than the plan implies.** The plan flagged the Sports Reference CBB scraper as "stubbed"; in reality the Sprint 81 implementation was already complete with both leaders-page and player-profile scraping logic. Only thing needed was `FIXTURE_PREFIX`. Plan-stage grep on the actual files would have caught this in 30 seconds.
- **The OOM incident → next-sprint hardening pattern is repeating again.** Sprint 86 hotfix → Sprint 87 fix; Sprint 97 hotfix → Sprint 98 hardening; today's OOM → Sprint 100 Stream D. The pattern works but suggests a more proactive capacity/load posture would prevent the incident in the first place. CPX11 → CPX21 upgrade (option 2 from today's debug conversation) remains an open path if 1-worker latency proves insufficient.
