# Sprint 30 Closeout

**Sprint:** 30
**Date:** 2026-04-02
**Owner:** Codex
**Status:** Final

---

## Shipped

- Removed request-time `nba_api` rescue from core player profile, career stats, game-log, and standings reads; these surfaces now return DB-first readiness metadata instead
- Added queue-backed warehouse refresh flows and readiness coverage for player profile, career, game logs, and shot charts
- Extended player and compare UI states so `ready`, `stale`, and `missing` are explicit instead of implying live upstream rescue
- Shipped the first CourtVue chart system layer plus premium visualization upgrades across player, compare, and insights surfaces
- Added backend coverage for DB-first user reads and verified the backend/frontend build pipeline

## Deferred / Not Finished

- Some non-core routes still rely on `sync_player_if_needed`, including parts of the advanced/trend-report layer
- The Usage vs Efficiency page is functionally improved, but copy/layout polish is still needed for the score explanation and spacing edge cases
- The new visualization language has landed on priority surfaces only; broader rollout remains future work

## Coordination Lessons

- Sprint closeout docs need to be written before merge instead of left implied by chat state
- Visual polish loops are easier to manage when the underlying metric definitions are pulled from backend code first, then reflected in UI copy

## Workflow Lessons

- When a page “works” but users still cannot read it quickly, treat that as a product bug, not a cosmetic follow-up
- Keeping DB-first readiness semantics consistent across backend and frontend made verification much easier than route-specific fallback behavior

## Technical Lessons

- Readiness metadata (`data_status`, `last_synced_at`) scales well across domains and is a better contract than hidden live-fetch fallback
- Signature chart work is most successful when built on shared tokens/primitives first and only then specialized for each workflow

## Next Sprint Seeds

- Finish the remaining non-core `nba_api` cleanup so advanced and trend-report routes are DB-first too
- Polish the Usage vs Efficiency explanation and continue simplifying any insight that still feels over-encoded
- Expand the CourtVue visualization language to additional high-value surfaces like standings, team pages, and pre-read
- Add operator-facing readiness monitoring and recovery ergonomics for the new queued enrichment domains
