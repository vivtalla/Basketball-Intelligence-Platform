# Sprint 94 Closeout — On/Off Impact Command Center

**Branch:** `feature/sprint-94-on-off-impact-revamp`
**Closed:** 2026-05-08

## What shipped

A complete revamp of the on/off impact surface into a coaching-grade command center. The previous leaderboard was a 4-column table (On Min, On Net, Off Net, On/Off Diff) with no side-of-ball decomposition, no team baseline context, and no confidence signaling. The player profile view was a plain 5-stat grid. Sprint 94 replaces both with a purpose-built analytical surface using data that was already in the database.

**No schema changes.** All derived fields are computed at query time from `PlayerOnOff`, `LineupStats`, `SeasonStat`, and `TeamSeasonStat`.

Single branch, 1 commit, 18 files changed (+1,944 / −146). 552 backend tests (was 513, +39 new across 2 service test files counted at close), 0 lint errors/warnings, `npm run build` clean.

---

### Stream A — Backend Pydantic Models (`backend/models/stats.py`)

7 new models added before `PbpCoverage`:

- `ImpactClassification` (str Enum): Two-Way Elite / Offensive Engine / Defensive Anchor / Neutral / Liability
- `ConfidenceTier` (str Enum): high / medium / low / insufficient
- `OnOffDecomposition`: ortg_impact, drtg_impact, marginal_net (Optional floats)
- `LineupSlot`: lineup_key, player_ids, player_names, net_rating, ortg, drtg, possessions, minutes
- `ExternalValidation`: rapm, epm, pipm, agreement_note
- `EnhancedOnOffStats`: flat struct with all `OnOffStats` fields + confidence_tier, impact_classification, decomposition, top_lineups, worst_lineups, external_validation, team_net_rating
- `EnhancedLeaderboardEntry`: player-level leaderboard row with ortg_impact, drtg_impact, marginal_net, confidence_tier, impact_classification, rapm, epm
- `EnhancedOnOffLeaderboardResult`: season + players list

---

### Stream B — Backend Service (`backend/services/on_off_impact_service.py`, NEW)

Batch-only; no N+1 queries anywhere.

**`_classify_impact(ortg_impact, drtg_impact) → Optional[ImpactClassification]`**
- TWO_WAY_ELITE if both > 3
- OFFENSIVE_ENGINE if ORTG > 3 and DRTG < 1
- DEFENSIVE_ANCHOR if DRTG > 3 and ORTG < 1
- LIABILITY if both < −2
- NEUTRAL otherwise
- Returns None if either input is None

**`_confidence_tier(on_minutes) → ConfidenceTier`**
- None/0 → INSUFFICIENT; ≥ 800 → HIGH; ≥ 400 → MEDIUM; ≥ 200 → LOW; else INSUFFICIENT

**`_lineup_slots_for_player(db, player_id, season, is_playoff, name_map, limit, worst)`**
- LIKE query on `lineup_key` + `possessions >= 100`
- Over-fetches 3× limit to account for LIKE false positives (e.g. player_id=12 matching "112-120-130")
- Post-filters by parsing `lineup_key.split("-")` and verifying the exact player_id is present
- Returns `limit` slots ordered by net_rating

**`build_enhanced_on_off(db, player_id, season, season_type) → EnhancedOnOffStats`**
- 404 if PlayerOnOff row not found
- Team net_rating via SeasonStat.team_abbreviation → Team.abbreviation → TeamSeasonStat
- Multi-team season: takes highest-GP SeasonStat row per player
- Agreement note: "Consistent with RAPM" if gap < 3; "Diverges from RAPM — small sample likely" if gap ≥ 8

**`build_enhanced_on_off_leaderboard(db, season, season_type, min_minutes, limit) → EnhancedOnOffLeaderboardResult`**
- 4 batch queries: PlayerOnOff rows → Player names → SeasonStat (for external metrics, highest GP per player) → TeamSeasonStat JOIN Team (builds abbr→net_rating dict in one query)
- Sorted by on_off_net descending

---

### Stream C — Backend Router (`backend/routers/advanced.py`)

- **Leaderboard** (`GET /api/advanced/on-off-leaderboard`): response_model upgraded to `EnhancedOnOffLeaderboardResult`; body replaced with `build_enhanced_on_off_leaderboard()`. Same URL, same query params — backward-compatible response superset.
- **New endpoint** (`GET /api/advanced/{player_id}/on-off-enhanced`): full `EnhancedOnOffStats` with decomposition, lineup slots, external validation.
- Original `GET /api/advanced/{player_id}/on-off` untouched.

---

### Stream D — Frontend Types + API + Hooks

- `types.ts`: appended `ConfidenceTier`, `ImpactClassification`, `OnOffDecomposition`, `LineupSlot`, `ExternalValidation`, `EnhancedOnOffStats`, `EnhancedLeaderboardEntry`, `EnhancedOnOffLeaderboardResult`
- `api.ts`: added `getEnhancedOnOffLeaderboard()` and `getEnhancedPlayerOnOff()`
- `usePlayerStats.ts`: added `useEnhancedOnOffLeaderboard()` and `useEnhancedPlayerOnOff()` SWR hooks

---

### Stream E — Leaderboard Revamp (`frontend/src/app/player-stats/page.tsx`)

Old: 4-column table with a text input for min-minutes filter.

New:
- **Min-minutes toggle**: 3-button (200 / 400 / 800) matching confidence tier thresholds
- **Classification filter pills**: All / Two-Way Elite / Offensive Engine / Defensive Anchor / Neutral / Liability
- **"Quadrant View" toggle**: shows `ImpactScatterChart` (ORTG Δ × DRTG Δ scatter, bubble size = on-court minutes)
- **9-column sortable table**: # / Player (with inline badge) / Team / On Min / ORTG Δ / DRTG Δ / On/Off (teal accent, default sort) / vs Team / Confidence
- **Click-to-expand rows**: inline On Net / Off Net / ORTG On / DRTG On / RAPM / EPM + "Full profile →" link
- New `ImpactScatterChart.tsx` in `frontend/src/components/on-off/`

---

### Stream F — Player Profile On/Off Panel

Replaced the 5-stat grid in `PlayerPbpInsights.tsx` (lines 200–228) with `<OnOffImpactPanel>`. All 7 sub-components are new files in `frontend/src/components/on-off/`:

| Component | Purpose |
|-----------|---------|
| `OnOffImpactPanel.tsx` | Main panel; fetches `useEnhancedPlayerOnOff`; loading skeleton; retry |
| `OnOffImpactBadge.tsx` | Classification pill; border style mirrors confidence tier (solid/dashed/dotted) |
| `OnOffConfidenceCallout.tsx` | Tier chip with minutes label |
| `OnOffDecompositionBar.tsx` | Recharts BarChart for ORTG Δ / DRTG Δ; reference lines at 0 and ±3 |
| `OnOffLineupPanel.tsx` | Two-column top/worst lineup grid; player name chips + net_rating + possessions |
| `OnOffExternalValidationPanel.tsx` | RAPM/EPM/PIPM chips + agreement note + attribution disclaimer |
| `OnOffMethodologyDrawer.tsx` | Collapsible `<details>` with formulas, thresholds, caveats |

Removed: `SmallMetric`, `ImpactNote`, `fmtSigned` helper functions from `PlayerPbpInsights.tsx` (no longer used after the grid replacement).

---

### Stream G — Tests (`backend/tests/test_on_off_impact_service.py`, NEW)

17 tests, all passing:

| Test | What it proves |
|------|---------------|
| `test_classify_two_way_elite` | Both > 3 → TWO_WAY_ELITE |
| `test_classify_offensive_engine` | ORTG > 3, DRTG < 1 → OFFENSIVE_ENGINE |
| `test_classify_defensive_anchor` | DRTG > 3, ORTG < 1 → DEFENSIVE_ANCHOR |
| `test_classify_liability` | Both < −2 → LIABILITY |
| `test_classify_none_when_none_inputs` | None inputs → None |
| `test_confidence_tier_thresholds` | 900/600/300/100/None → HIGH/MEDIUM/LOW/INSUFFICIENT/INSUFFICIENT |
| `test_build_enhanced_on_off_decomposition` | ortg_impact, drtg_impact, marginal_net, classification computed correctly |
| `test_build_enhanced_on_off_lineup_slots` | 2 qualifying + 1 < 100 poss + 1 LIKE false positive → 2 returned |
| `test_build_enhanced_on_off_missing_team_stat` | No TeamSeasonStat → marginal_net None, team_net_rating None |
| `test_build_enhanced_on_off_external_validation_consistent` | RAPM gap < 3 → "Consistent" note |
| `test_build_enhanced_on_off_external_validation_diverges` | RAPM gap ≥ 8 → "Diverges" note |
| `test_build_enhanced_on_off_not_found` | Missing PlayerOnOff → 404 |
| `test_build_leaderboard_min_minutes_filter` | 150 min player excluded at min_minutes=200 |
| `test_build_leaderboard_ordered_by_on_off_net` | Result is descending by on_off_net |
| `test_build_leaderboard_ortg_drtg_impact_computed` | ortg_impact and drtg_impact set correctly on leaderboard entries |
| `test_build_leaderboard_external_metrics_surfaced` | RAPM from SeasonStat surfaces on leaderboard |
| `test_lineup_slot_false_positive_filter` | "112-120-130" is false positive for player 12; "12-50-80" is true positive |

---

### Methodology docs (`specs/platform-methodology.md`)

New §13 "On/Off Impact Command Center" covering computed fields, classification thresholds, confidence tiers, lineup context qualification, external validation agreement logic, caveats, and implementation file references.

---

## Verification

```
backend tests: 552 passed, 1 pre-existing failure (test_playoff_sync::test_daily_sync_post_game_dry_run — fails on master too)
npm run build: clean (28 static + 6 dynamic pages)
npm run lint: 0 errors, 0 warnings
```

---

## Production deploy plan

1. Merge `feature/sprint-94-on-off-impact-revamp` → `master` → Vercel auto-deploys frontend (~2 min).
2. `ssh ubuntu@5.78.114.15 && cd /home/ubuntu/bip && git pull origin master && sudo bash infra/deploy.sh` — backend deploy (no migration required).
3. Smoke test new leaderboard endpoint: `curl "https://api.courtvue.app/api/advanced/on-off-leaderboard?season=2024-25" | python3 -c "import json,sys; p=json.load(sys.stdin)['players'][0]; print(list(p.keys()))"` — confirm `ortg_impact`, `drtg_impact`, `confidence_tier`, `impact_classification` in keys.
4. Smoke test new player endpoint: `curl "https://api.courtvue.app/api/advanced/2544/on-off-enhanced?season=2024-25" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['confidence_tier'], d['impact_classification'], d.get('decomposition'))"`.
5. Browser: load `/player-stats` → On/Off tab → verify 9-column table, classification filter pills, Quadrant View. Load any player profile → PBP Insights section → verify `OnOffImpactPanel` renders with badges and decomposition bars.

---

## Deferred

None. Every plan item shipped.

Candidates for a future sprint (all "different domain" sister features):
- Opponent-tier breakdown (on/off per opponent DRTG quartile — requires stint-level attribution)
- RAPM via ridge regression from raw stints (major analytical lift, data science domain)
- Playoff vs Regular Season on/off comparison view

---

## Workflow notes

- The LIKE false-positive problem for `lineup_key` lookups (player_id=12 matching "112-120-130") is a subtle data quality issue worth remembering. The 3× over-fetch + post-filter pattern handles it cleanly without changing the schema.
- Removing `SmallMetric`, `ImpactNote`, and `fmtSigned` from `PlayerPbpInsights.tsx` was correct — they were only used by the replaced block. The lint pass confirmed no other references.
- `usePlayerOnOff` was kept in `PlayerPbpInsights.tsx` (alongside the new `OnOffImpactPanel`) because `onOff` and `onOffError` still drive the coverage/error/noData display logic above the main content section. The inline ORTG/DRTG Off mini-card in the clutch row also still uses it. No orphaned hook.
