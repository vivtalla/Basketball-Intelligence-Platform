# Sprint 89 Closeout — Team-Side Player Fit (Roster + League)

**Branch:** `feature/sprint-89-team-roster-fit`
**Worktree:** `/Users/viv/Documents/bip-s89`
**Closed:** 2026-05-03

## What shipped

Single-stream sequential sprint. 4 commits, 1 sprint branch, end-to-end backend → frontend → tests → docs.

The new `fit` tab on `/teams/[abbr]` answers two questions that the platform had no surface for:

1. **"How well does each of my own players fit this roster?"**
2. **"Which players around the league would fit my team?"**

Both are scored with the same 3-component weighted-sum model the player-side `team_fit_v3` already uses (45% Skill Supply / 30% Teammate Overlap / 25% Role Runway on 13 z-scored role features), inverted: fix the team, score many players.

### Stream A — Backend service (`249678a`)

`backend/services/team_roster_fit_service.py` (NEW, 350+ LOC) and `backend/models/team_roster_fit.py` (NEW). Reuses `_score_team_fit`, `_team_overlap_flags`, `_build_drivers`, `_feature_team_best`, `_bucket_runway_bonus`, `_position_bucket`, `_confidence_for_team`, and `WEIGHTS` from `team_fit_service` directly — same math, no duplication, no drift. Adds:

- **Self-exclusion** for current-roster scoring (subject is removed from the comparison roster so Role Competition isn't inflated by self-overlap).
- **`team_need_vector`**: roster-weighted average z per feature (weighted by `min_pg`, floored at 0.5 so deep bench still counts a little). Negative z surfaces as `primary_needs`, positive as `primary_strengths`. Deduped across `SIMILARITY_STATS_V2` (which lists `stl_pg`/`blk_pg` twice with the 0.6 weight) so labels don't double-list.
- **Position-cohort percentile** (G / F / C) computed via per-(season, bucket, feature) mean/std. Display-only — the score formula keeps using global norms so cross-position rankings stay coherent. Surfaces as `cohort_percentiles[]` per player, sorted by absolute z (most-distinctive features first), top 3.
- **Methodology block** in the response payload with explicit disclosures (no salary / availability, no shot location overlap, no defensive scheme, coarse position bucket).
- AGENTS.md kicked off into Sprint 89 in the same commit.

### Stream B — API endpoint + cache (`a36c8e8`)

`GET /api/teams/{abbr}/roster-fit?season=...&season_type=...&limit=N` mounted on the existing teams router (matches the Sprint 86 pattern that added `/tracking` and `/hustle` inline rather than via a new router file — no `main.py` change needed).

24h SQLite `cache.db` TTL keyed on `(abbr, season, season_type, limit)`. Cold compute is ~1-7s depending on data size; cache hit is <50ms. Aligns with the daily-sync cadence (underlying `season_stats` only changes nightly). Pydantic round-trip via `.model_dump(mode="json")` → store → `TeamRosterFitResponse(**cached)` hydrate; verified in tests.

Local smoke (real DB):
- Cold (OKC): 2.3s
- Warm: 40ms
- BOS top candidate: Giannis @ 88.2; OKC top candidate: Jokić @ 87.9; cache stats counter increments correctly.

### Stream C — Frontend (`77fdcce`)

New `fit` tab inserted between `lineups` (7) and `arc` (8) on `/teams/[abbr]`. `TeamRosterFitPanel.tsx` (NEW, 400+ LOC) renders:

- **Team need vector card**: primary needs + primary strengths chips with z-scores.
- **Current roster table**: every rostered player ranked by fit, sortable by Fit / Skill / Runway / Solo, click-to-expand for full driver + overlap + cohort-percentile breakdown.
- **League candidates grid**: top 25 statistical fits as cards with position filter (ALL / G / F / C), click-to-expand details, deep-links to `/players/{id}` and `/teams/{abbr}`.
- **Methodology drawer**: weights, duplicate threshold, cohort caveat, explicit "no salary / availability" disclosure, generated_at timestamp.

Reuses the visual language of the existing player-side `TeamFitPanel`: score-tone tinting (green ≥70 / amber ≥55 / muted), confidence pills, driver/overlap chip components.

`types.ts` and `api.ts` extended append-only per the lock-table convention. New `useTeamRosterFit` SWR hook in `hooks/`.

### Stream D — Tests (`eb01ed5`)

`backend/tests/test_sprint89_team_roster_fit.py` — 9 tests, all pass. Backend suite goes 500 → **509**, zero regressions.

Coverage:
1. report shape + methodology version pinned to `team_roster_fit_v1`
2. self-exclusion: a current-roster player never appears as their own overlap teammate
3. position-cohort percentile is tagged with the player's own bucket, not the team-average bucket
4. low-confidence path: thin rosters (<3 qualified rows) emit a warning AND skip league-candidate scoring entirely
5. team need vector surfaces the right primary need on a deliberately constructed 3-point-poor roster (`par3` → "Spacing")
6. cache round-trip via SQLite CacheManager hydrates to identical model
7. unknown team raises 404
8. determinism: two calls with identical args produce identical payloads (modulo `generated_at`)
9. league candidates exclude the team's own roster (no overlap with `current_roster_fits`, no `current_team_abbr == team`)

### Stream E — Documentation (this commit)

`specs/platform-methodology.md` extended with a "Team-Side Roster Fit (Sprint 89)" subsection under §6 (Player Archetypes, Similarity, and Team-Fit). Documents weights, features, position-cohort approach, self-exclusion rule, confidence bands, caching strategy, and limitations.

## Verification

Pre-merge:
- `pytest -q`: **509 passed**, 2 warnings (unchanged FastAPI on_event deprecation)
- `npm run build`: clean
- `npm run lint`: 0 errors / 0 warnings
- Local curl smoke confirmed cold compute, warm cache, and cache stats endpoint
- Cross-team smoke (OKC, BOS) returns plausible needs + plausible top candidates (Jokić for OKC, Giannis for BOS)

## Methodology summary

```
fit_score = 0.45 · skill_supply  +  0.25 · roster_need  +  0.30 · role_competition_inverse
```
on a 0–100 scale.

**13 features (z-scored per season):** pts_pg, reb_pg, ast_pg, stl_pg, blk_pg, tov_pg, ts_pct, usg_pct, per, par3, ftr, stl_pg (×0.6), blk_pg (×0.6).

**Confidence bands:** high (≥8 qualified rows + ≥20 GP), medium (3–7 rows), low (<3 rows; gates league-candidate scoring entirely).

**Explicit disclosures (in the methodology drawer):**
- Statistical fit only — does not consider salary, contract length, free-agent status, age, injury history, or trade feasibility.
- Same-season comparisons only — no projections.
- 13 box-score-derived features; does not include shot location overlap, defensive scheme, or play-type fit.
- Position cohort is coarse (G / F / C); does not distinguish stretch-4 vs traditional PF.

## Deferred

None this sprint. Every plan item shipped end-to-end.

## Sprint 90 candidates (filed in BACKLOG)

Per the Deferral Policy these are **different domain** (sister features), not "follow-on polish":

- **Salary + contract integration → trade-feasibility filtering.** Today's league candidates are statistical fit only. A future sprint could ingest Spotrac contract data and let the user filter the candidates grid to "trade-feasible within $X of expiring" or "free agents next summer."
- **Shot location overlap.** Build per-team shot-zone profiles and per-player zone-share vectors, then add a fit component scoring spacing/diet compatibility (a guard who only shoots above-the-break 3s shouldn't score perfectly against a roster already bursting with above-the-break shooters).
- **Defensive scheme clustering.** Use the Sprint 88-populated tracking + hustle data to cluster teams by defensive identity (switch-heavy / drop / ice / aggressive trap), then add a defender-fit signal scoring whether a candidate defender's profile matches the team's scheme.
- **Play-type compatibility via Synergy data.** Score whether a candidate's high-frequency play types complement (or duplicate) the team's existing offensive distribution.

## Workflow lessons

- **The refactor commit I planned wasn't worth the diff churn.** Stream A.1 in the original plan was an "extract internals into a shared module" commit. On reflection it would have moved code without changing behavior — and importing the underscore functions from `team_fit_service` directly achieves the same single-source-of-truth guarantee. Skipped it; saved a commit and ~50 lines of churn. (Lesson generalizes: don't introduce abstractions ahead of the second caller actually needing them.)
- **Stale worktree git lock from a prior sprint.** When I first staged Stream A, git showed thousands of "deleted" files because a stale `.git/worktrees/bip-s89/index.lock` from a prior aborted session was holding a corrupted index. Removed the lock, re-`git reset HEAD`, and the index reverted to the actual state. Worth flagging because the same stale-worktree pattern from Sprint 78/85/86 worktrees is still littering `/Users/viv/Documents/bip-*` — those should be pruned at some point but didn't block Sprint 89.
- **Worktree node_modules — symlinking out-of-tree breaks Turbopack.** `ln -sf` from canonical `node_modules` failed with `Symlink [project]/node_modules is invalid, it points out of the filesystem root`. The fix was a real `npm install --prefer-offline` in the worktree (15 s with cache warm). Document for next sprint: just install fresh, don't try to symlink across the canonical → worktree boundary.
- **Frontend test gap.** This sprint added zero new frontend tests. The build + lint pass is the safety net for the new components. Backend test count covers methodology contract + payload shape, which is what changes most often. Keeping frontend test infra as a Sprint-90+ candidate when there's a real defect to regress against.
