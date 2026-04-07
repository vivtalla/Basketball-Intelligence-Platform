# Sprint 43 Architecture Audit

**Sprint:** 43  
**Date:** 2026-04-06  
**Owner:** Codex

---

## Findings

### 1. Runtime schema mutation was still part of normal app startup
- `backend/main.py` was calling both `Base.metadata.create_all()` and `apply_schema_updates()` on every startup.
- `backend/db/ensure_schema.py` had become the de facto migration system, mixing table creation, additive column drift, data backfills, and constraint rewrites.
- This made schema behavior implicit, environment-sensitive, and difficult to reason about safely.

### 2. A request-time sync seam still existed in the serving layer
- `POST /api/advanced/{player_id}/sync-pbp` was explicitly a sync endpoint, but the route still pre-ran `sync_player_if_needed()`, which blurred the line between local-data reads and upstream fetch behavior.
- The platform has otherwise been moving toward DB-first / queue-backed behavior, so this was an architectural outlier.

### 3. Decision intelligence had unclear ownership
- Core lineup-impact, play-type EV, matchup-flags, and follow-through logic lived in `backend/routers/decision.py`.
- Older service files (`lineup_impact_service.py`, `matchup_flag_service.py`, `follow_through_service.py`) still existed with divergent logic and payload shapes.
- Scouting and tests were importing decision builders from the router layer instead of a canonical service layer.

### 4. Legacy compatibility rules were still implicit
- Team prep and team intelligence had their own separate “modern season” checks.
- Legacy responses were still described as `legacy-plus-derived`, which did not cleanly distinguish “compatibility mode” from “canonical runtime path.”

### 5. Some silent fallbacks still hid important context
- `stats_service.py` and `sync_service.py` still swallowed advanced-stats fetch failures silently.
- These weren’t platform blockers, but they made operational diagnosis harder than it needed to be.

---

## Shipped Remediations

### Migration system
- Added Alembic scaffolding under `backend/alembic/` with:
  - `0001_base_schema`
  - `0002_legacy_schema_drift`
- Added `backend/db/migrations.py` as the canonical programmatic migration entry point.
- Replaced `ensure_schema.py` with a compatibility wrapper that now delegates to Alembic-backed upgrade logic.
- Removed runtime schema mutation from FastAPI startup.

### Runtime data-path discipline
- Removed the remaining request-time player bootstrap from the advanced PBP sync route.
- Preserved explicit sync endpoints and queued enrichment workflows, but stopped letting normal serving behavior “helpfully” mutate local state at runtime.

### Decision-stack ownership
- Moved the shipped decision builders into `backend/services/decision_support_service.py`.
- Reduced `backend/routers/decision.py` to transport-only route handlers.
- Updated scouting and tests to depend on the service layer instead of router-local business logic.
- Replaced the older decision helper service files with thin compatibility wrappers so duplicate logic no longer exists in parallel.
- Removed the remaining `decision_support_service -> routers.styles` dependency by switching the decision stack onto lighter service-owned style snapshots and matchup summaries.

### Runtime policy clarity
- Added `backend/services/runtime_data_policy.py` to centralize the warehouse-first versus legacy-compatibility rule.
- Extended team and pre-read responses with additive `runtime_policy` metadata.
- Reframed historical-season canonical-source reporting from `legacy-plus-derived` to `legacy-compatibility`.

### Code-quality cleanup
- Replaced silent advanced-stats fetch failures with debug logging in `stats_service.py` and `sync_service.py`.
- Removed stale `type: ignore` pressure in the decision stack by moving severity/confidence handling onto typed helpers.

---

## Remaining Debt

### 1. Router/service boundary cleanup is still incomplete outside decision intelligence
- `routers/styles.py` still exposes business-logic builders that other layers import.
- Other domains still have some transport/business-logic mixing that Sprint 43 did not fully normalize.

### 2. Legacy compatibility is isolated more clearly, but not retired
- Historical workflows still rely on legacy tables for some reads.
- The code now labels that mode more honestly, but it does not eliminate historical compatibility dependencies.

### 3. Wider router/service cleanup is still unfinished outside the decision stack
- The decision stack no longer imports router-local style builders, but other domains still mix transport and business logic more than they should.
- Sprint 43 fixed the highest-signal seam without attempting a repo-wide purity rewrite.

### 4. Silent fallback cleanup is not exhaustive
- Sprint 43 addressed the high-signal silent-failure paths in the core sync/stats layer, but some lower-level ingestion and client fallback chains still merit future tightening.

---

## Approved Rules Going Forward

- Schema evolution must go through Alembic migrations, not app-startup DDL helpers.
- Product-serving routes should not perform surprise upstream sync or enrichment.
- Router modules should transport requests and responses; canonical business logic belongs in services.
- Legacy historical support must stay behind explicit compatibility boundaries rather than being interwoven into modern runtime paths.
- Additive readiness/runtime metadata is preferred over hidden “best effort” repairs during reads.
