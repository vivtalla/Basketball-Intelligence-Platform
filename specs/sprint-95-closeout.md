# Sprint 95 Closeout — Lineup Lab

**Branch:** `feature/sprint-95-lineup-lab`
**Merged:** TBD
**Date:** 2026-05-08

---

## Summary

Built the Lineup Lab — a dedicated `/lineups` page with a league-wide leaderboard and an interactive What-If Studio. All derived metrics (Bayesian-shrunk net rating, net vs team baseline, archetype classification, confidence tiers, player removal impacts) are computed at query time from existing `lineup_stats + players + teams + team_season_stats`. No schema changes.

---

## Deliverables

### Backend — 5 new files

| File | Purpose |
|------|---------|
| `backend/models/lineups.py` | 6 Pydantic models: `LineupLeaderboardEntry`, `LineupLeaderboardResult`, `LineupBuilderRequest`, `PlayerRemovalImpact`, `LineupBuilderResult`, `SublineupsResult` |
| `backend/services/lineup_leaderboard_service.py` | Bayesian shrinkage, archetype classification, batch 3-query leaderboard builder |
| `backend/services/lineup_builder_service.py` | Exact match, partial overlap ranking, player-removal WOWY impacts |
| `backend/services/lineup_sublineup_service.py` | 2-man / 3-man combination aggregation via `itertools.combinations` |
| `backend/routers/lineups.py` | 3 endpoints: GET /leaderboard, POST /builder, GET /sublineups |

**3 new endpoints (registered in `backend/main.py` at prefix `/api/lineups`):**
- `GET /api/lineups/leaderboard` — sortable by 8 keys, team filter, min-possessions gate
- `POST /api/lineups/builder` — exact + partial match with player-removal impact grid
- `GET /api/lineups/sublineups` — 2-man / 3-man aggregated combos per team

**Backward compatible:** `/api/advanced/lineups` untouched.

### Backend — 32 new tests (581 total, was 549)

| Test file | Tests | Coverage |
|-----------|-------|---------|
| `test_lineup_leaderboard_service.py` | 18 | Confidence levels, shrunk formula, all 5 archetypes + unclassified, season/team/poss filters, sort direction, graceful missing team stat |
| `test_lineup_builder_service.py` | 8 | Exact match, sorted key (order-independence), partial match, no match, removal impact, delta sign, small-sample warning, false-positive filter |
| `test_lineup_sublineup_service.py` | 6 | C(5,2)=10, C(5,3)=10, poss gate, aggregation across lineups, weighted net rating, sorted output |

### Frontend — 10 new files, 5 modified

**New `/lineups` page** (`frontend/src/app/lineups/page.tsx`):
- Tab 1 — **Leaderboard**: season, season-type, team, and min-possessions filters; ORTG×DRTG scatter chart toggle; sortable 12-column table
- Tab 2 — **What-If Studio**: 5 fixed player-slot dropdowns (hooks pre-allocated per CLAUDE.md rule), submit returns match quality banner + exact/closest lineup cards + player removal impact grid

**7 new components in `frontend/src/components/lineups/`:**
| Component | Purpose |
|-----------|---------|
| `LineupLeaderboardTable.tsx` | 12-column sortable table; `compact` prop for sub-lineup sections |
| `LineupScatterPanel.tsx` | ORTG×DRTG Recharts scatter; Y-axis reversed (lower DRTG = better = top); bubble radius ∝ sqrt(minutes); color by archetype |
| `LineupArchetypePill.tsx` | Archetype label pill: Elite=teal, Offensive Wall=amber, Defensive Wall=indigo, Balanced=gray, Negative=red |
| `LineupConfidenceBadge.tsx` | Confidence badge with possessions count inline |
| `LineupBuilderPanel.tsx` | 5 searchable player slots; Build/Reset buttons |
| `LineupBuilderResults.tsx` | Match quality banner + exact/closest cards + player removal grid |
| `LineupMethodologyDrawer.tsx` | Collapsible `<details>`: shrinkage formula, archetype rules, confidence thresholds, caveats |

**Modified files:**
- `frontend/src/lib/types.ts` — 8 new types (2 type aliases + 6 interfaces)
- `frontend/src/lib/api.ts` — 3 new API functions
- `frontend/src/hooks/usePlayerStats.ts` — 2 new SWR hooks
- `frontend/src/components/NavLinks.tsx` — "Lineup Lab" added to More dropdown
- `frontend/src/app/teams/[abbr]/page.tsx` — 2-man + 3-man sub-lineup sections in lineups tab

### Methodology doc
- `specs/platform-methodology.md` — §14 Lineup Lab added (computed fields, archetype classification, What-If mechanics, sub-lineup aggregation, caveats)

---

## Verification

- **Backend tests:** 32 new, 581 total passing (excluding pre-existing `test_playoff_sync.py::test_daily_sync_post_game_dry_run` failure on master)
- **`npm run build`:** clean (TypeScript ✓, Turbopack ✓)
- **`npm run lint`:** 0 errors, 0 warnings
- **Pre-existing failure confirmed:** `test_playoff_sync.py::test_daily_sync_post_game_dry_run` fails on master with no sprint-95 changes — not introduced by this sprint

---

## Deferred

None. Sprint is self-contained.

---

## Patterns Reused from Sprint 94

- LIKE + 3× over-fetch + post-parse false-positive filter (`lineup_key.split("-")` to reject player_id=12 matching "112-120-130")
- Bayesian shrinkage prior (150.0) from `decision_support_service.py`
- Batch Player + TeamSeasonStat queries (zero N+1)
- Methodology drawer `<details>` collapsible pattern
- Archetype pill styling
