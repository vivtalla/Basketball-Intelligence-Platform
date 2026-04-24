# Sprint 65 Closeout

**Sprint:** 65 — Scouting & Opportunity Fit
**Date:** 2026-04-23
**Owner:** Claude (single-stream sprint; no Codex workstream)
**Status:** Final

---

## Shipped

- In-process TTL cache on `build_opportunity_report` keyed by `(season, team, min_minutes, position, date)`; 10 min current-season, 24 h historical. Hot path `team=ALL` scouting traversals no longer recompute per tab-open.
- `OpportunityCompareHandoff` pre-computed on every top-row (pinned id + top 3 same-bucket peers drawn from the full pool). RoleFitCard ships a "Compare with peers →" CTA.
- Role-Fit depth: AST/G + TOV/G rows with cohort averages and delta column, alongside existing 3PA/FTr/eFG%.
- Directional-hint gate made explicit: `confidence ∈ {high, medium}` AND `len(hint_basis) ≥ 2`; no orphan basis chips when gated out.
- `ClaimInferenceConfidence` on every scouting claim (level + reasons + anchored/opponent-specific counts + evidence-source diversity); `_rank_claims_by_confidence` reorders claims per section so opponent-backed high-confidence surfaces first; `ScoutingClipAnchor.opponent_specific` flag set.
- ScoutingReportView renders a colored confidence pill + "Compare with this claim →" link carrying `source=scouting&claim_title&claim_reason`.
- Compare page inbound-context banners for `source=opportunity` and `source=scouting`; Pre-Read page mirrors the scouting banner on deep-links.
- `UsageEfficiencyDashboard.tsx` → `OpportunityDashboard.tsx` (import + rename); three stale pre-Sprint-58 files deleted (`usage_efficiency_service.py`, `UsageBurdenMatrix.tsx`, `UsageLoadBoard.tsx`); orphan `UsageEfficiencyPlayerRow` TS interface removed.
- Bugfix: `_position_bucket` now handles compound positions like `Guard-Forward` / `SG/SF` (split on `-` / `/`, take primary token; full-word forms added to map). Jaylen Brown and the rest of BOS no longer collapse to bucket `"other"`.
- Bonus fix: `TeamNetRatingChart` Tooltip `formatter` value type loosened to `ValueType | undefined` — `npm run build` type-check was failing on master since Sprint 64.

**Test deltas:** 13 new backend tests (6 opportunity cache/handoff/role-fit/hint, 7 scouting confidence) + 1 regression test for compound position bucketing. Full backend suite 193 passing; frontend `npm run lint` clean; `npm run build` now passes end-to-end.

## Deferred / Not Finished

- Scouting → Pre-Read claim-specific deep-link wiring is in place (banner renders) but there is no affordance *inside* the scouting view to jump to Pre-Read for a specific claim yet — only Compare. Natural follow-on.
- Printable/CSV/Markdown exports and snapshot-naming were *explicitly out of scope* per the approved plan; still open backlog items.
- No league-wide peer set for Compare handoff — peers come from the backing report, so `team=BOS` yields BOS-only peers. Cross-league positional peers would need a second `team=ALL` request or a backend-side peer expansion.

## Coordination Lessons

- Plan-mode prompt to `AskUserQuestion` correctly branched us into the "Scouting & Opportunity Fit" track instead of my initial "Coaching Packet" recommendation. Offering the recommended option first and letting the user divert saved a full re-plan.

## Workflow Lessons

- Shared file claims were pre-declared in `AGENTS.md` at kickoff; single-stream sprint meant no contention, but the table still served as a useful scope fence (prevented me from wandering into unowned files).
- Hot-reload on the already-running dev servers (`uvicorn --reload` + Next.js) let the user see the Jaylen Brown fix within seconds of the commit. No need to restart anything.

## Technical Lessons

- **Compound NBA positions are common** — not a corner case. `Guard-Forward`, `Forward-Center`, `SG/SF` show up on starters, not edge-of-roster guys. Any bucketing logic that uses a flat enum map **must** pre-split on `-` / `/`. This is the second sprint where position-bucket handling caused a user-visible bug; worth codifying a shared helper if a third caller appears.
- `Compare` page `p1`/`p2` contract is pairwise; Sprint 65 honored that and encoded extra peer ids as a `peers=` hint param. A genuine multi-player compare surface would require a Compare-page refactor, not just a param addition.
- Opportunity cache uses `time.monotonic()` + a `date.today().isoformat()` bucket in the key. This gives graceful midnight invalidation after the nightly sync without requiring an explicit cache bust. Same pattern would work for the trend/trajectory services if they ever need caching.

## Next Sprint Seeds

1. **Cross-league positional peers for Compare handoff** — when the user hits Compare-with-peers from a team-scoped opportunity view, optionally expand peer lookup to the league-wide pool for the same bucket (requires either a second `team=ALL` call or a dedicated `/api/insights/opportunity/peers` endpoint).
2. **Shared position-bucket helper** — lift `_position_bucket` out of `opportunity_service.py` into a small `services/positions.py` and switch `trajectory_service` + any future callers to it. The regression in Sprint 65 would have been caught earlier if there was one authoritative implementation.
3. **Scouting claim → Pre-Read deep-link inside ScoutingReportView** — today the claim banner renders on Pre-Read but there is no per-claim jump-to-pre-read affordance. Natural symmetry with Compare-with-this-claim.
4. **Printable coaching packets** — deferred from the rejected Sprint-65 "Coaching Packet" option. Shareable/CSV output across prep + compare + trends + clip-list is still the biggest single lift for staff daily workflow.
5. **Inference-confidence surfacing elsewhere** — the `ClaimInferenceConfidence` model is claim-level; similar honest calibration would pay off on focus-levers, what-if scenarios, and decision-tool rotation suggestions.

## Backlog Refresh

- Remove "consider renaming `UsageEfficiencyDashboard.tsx`" from *Opportunity Workspace Follow-Ons* (shipped).
- Remove "add short-lived Opportunity score caching keyed by season/team/minutes/position" from *Opportunity Workspace Follow-Ons* (shipped).
- Remove "add compare handoff with pinned player plus top positional peers" (shipped, though with same-team scope — re-add as "cross-league peer expansion").
- Downgrade *Play-Type Scouting* "strengthen inferred action-family confidence" — this shipped; what remains is opponent-specific claim sourcing beyond what our limited PBP fallback supports.
