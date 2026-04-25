# Sprint 68 Closeout

**Sprint:** 68 — Decision Intelligence Follow-Ons
**Date:** 2026-04-25
**Owner:** Claude (single-stream sprint, all five Sprint-67 backlog items closed on one branch in one session)
**Branch:** `feature/sprint-68-decision-intelligence-followups`
**Status:** Final

---

## Theme

Close out the five Sprint-67 deferrals so the Decision Intelligence surface is a finished product instead of a feature with known gaps. No new theme, no new architecture — pure follow-through on items the previous sprint named explicitly.

---

## Shipped

### 1. Opportunity `usg_pct` display precision

`OpportunityPlayerRow.usg_pct` was rounded to one decimal place, which collapsed `season_stats.usg_pct` values like `0.285` (Jokić), `0.301` (Tatum), and `0.336` (SGA) into an identical `0.3` display on the Sprint-67 scouting brief. Bumped `round(x, 1)` to `round(x, 3)` in `services/opportunity_service.py`. Live smoke confirms the brief now reads "Usage 28.5% / 30.1% / 33.6%" for the three.

### 2. Team-Fit Similarity Mode (B10 from Sprint 67)

Removed the `NotImplementedError` and 501. The teammate-duplicate penalty is implemented at the **distance layer**, not the pool layer:

- `services/similarity_service.py` adds `_team_fit_weight_overrides()` which produces a per-feature multiplier dict for the subject. For each feature, if the subject's z-score is within 0.5 of any same-team teammate's z-score, that feature's distance weight is multiplied by 0.4 — features the team already covers contribute less to comp ranking and differentiators rise.
- New `_raw_z()` and `_weighted_vec()` helpers replace the inline z + weight composition so season / age / team_fit modes share the same distance machinery.
- Frontend Team-Fit tab now renders real comps; the deferred-state card and `!deferred` guards are gone.
- Live smoke on Tatum 2024-25: season mode returns Edwards / Franz / RJ Barrett (high-similarity wings), team_fit mode returns Luka / Zion / Scottie Barnes / LeBron — all heliocentric — once the Tatum + Jaylen Brown usage overlap is penalized. Different ranking, basketball-defensible reasoning.

### 3. Scouting-Brief Deep-Link Banners

Mirrors the Sprint-65 `source=opportunity` / `source=scouting` banner pattern from `/compare` and `/pre-read`, applied to deep links fired from the Scouting Brief cards.

- `scouting_brief_service.py` now threads `source=brief&card={card_type}` (and `&diagnosis_tag={top_tag_key}` for the Shot Profile card) into every card's `deep_link`.
- New `components/scouting-brief/BriefSourceBanner.tsx` renders a one-line "From Scouting Brief · {card label} · pinning {tag label}" pill above a named anchor when the URL carries `source=brief`. Hides itself for unrelated anchors so one deep link doesn't light every banner on the page.
- `PlayerDashboard` wraps the archetype block and Shot Lab block in `#archetype` / `#shot-lab` anchor wrappers with `<BriefSourceBanner>` slotted directly above each.

### 4. Coaching Copy Polish

Surgical pass on user-facing strings in shot diagnosis + scouting brief. Kept coach-idiomatic terms that were already strong (`Elite corner gravity`, `Dead corners`, `Elite rim pressure`); replaced data-science phrasing with direct vocabulary; dropped z-scores from headline summaries while keeping them in the evidence audit trail.

Renamed labels: `Mid-range dependency → Mid-range heavy`, `Rim finishing variance → Finishing below average at the rim`, `Low 3-point volume → Won't pull from 3`, `Long-two diet problem → Long-two habit`, `Foul-drawing creator → Gets to the line`, `Floor-spacer (low FTR) → Floor spacer`, `Heat-check overperformance → Running hot`. Evidence notes rewritten on every tag (tighter, less clinical). Headline format changed from `"{tag} with a {sustainability} shot profile — {creation}."` to `"{tag} · {sustainability} · {creation}."` (drops doubled "shot profile" framing).

Brief Strengths card summary drops `(z=+X.XX)` from the visible headline; z-scores stay in evidence rows. Usage & Efficiency card switches to bullet format ending in "{N}th cohort percentile". Shot Profile uses middot separators throughout.

### 5. Player Archetype Evolution Timeline

Multi-season archetype-per-year surface ported from the team Style-X-Ray movement pattern.

- `models/archetype.py` adds `ArchetypeHistoryEntry` (with `transitioned_from`, the previous season's key when year-over-year archetype changes) and `ArchetypeHistoryResponse`.
- `services/player_archetype_service.build_archetype_history(db, player_id)` enumerates a player's regular-season rows oldest → newest and runs `classify_player_archetype()` per season. The Sprint-67 per-season TTL-cached frame keeps repeated calls cheap.
- `GET /api/archetype/{player_id}/history` route. 404 when the player isn't in the warehouse, otherwise full timeline.
- New `ArchetypeEvolutionTimeline.tsx` vertical-timeline component with confidence-coded dots (green/amber/muted), per-season archetype labels, and `Transition` pills on year-over-year changes. Hides when history has fewer than two seasons. Wired into `PlayerDashboard` directly under `PlayerArchetypeProfile` in the archetype anchor section.

Live smoke on LeBron James (2020-21 → 2025-26): six entries; 2021-22 through 2025-26 classified as `heliocentric_creator` at high confidence; 2020-21 falls back to developmental due to thinner advanced-stat coverage that season.

---

## Deferred / Not Finished

Nothing from the Sprint-68 scope. The five Sprint-67 follow-ons are all closed.

Adjacent ideas that weren't in scope and remain backlog candidates:

- **Archetype peer-pool composition explainer** in the methodology drawer (which players are in the pool, what features were excluded for thin sample). Would unlock more transparency on borderline classifications like Lu Dort 2024-25 → `movement_shooter`.
- **Brief deep-link banners on `/insights`** (the Usage & Efficiency and Trajectory cards both link there with `source=brief` already; Sprint 68 only wired the player-page banners).
- **Team-fit explanation pill** on each Team-Fit tab comp showing which features were penalized for that subject. Currently the penalty is invisible in the UI even though it shifts rankings — a "Team has: usage, scoring → comp ranks for: defense, playmaking" hint would close the loop.

---

## Verification

- **Backend pytest:** **247 passed** (was 243 at Sprint-67 close). 4 new tests this sprint: 2 archetype-history tests + 2 team-fit tests (overrides unit + ranking-changes integration). Plus the existing 243 still green.
- **Frontend `npm run build`:** clean.
- **Frontend `npm run lint`:** 0 errors, only the same 7 pre-existing warnings in `usePlayerStats.ts`.
- **Frontend `tsc --noEmit`:** clean.
- **Live-DB smokes:**
  - Jokić / SGA / Tatum scouting brief: usage values now distinct (28.5% / 33.6% / 30.1%); coach-readable headlines after the polish pass.
  - Tatum 2024-25 similarity: season vs team_fit produce meaningfully different rankings, with team_fit promoting more heliocentric peers once the Jaylen Brown usage overlap is penalized.
  - LeBron 2020-21 → 2025-26 archetype history: continuous timeline, transition flagged on 2020-21 → 2021-22 (developmental → heliocentric).

---

## Coordination Lessons

- **Tight, ordered scope worked.** Five items, sequenced cheap-to-expensive (precision fix → team-fit → banners → copy → evolution), one branch, one session, no rework. Each item's commit was independently testable.
- **Re-using infrastructure paid off again.** The archetype evolution timeline didn't need a new classifier, a new cache, or a new schema — `build_archetype_history()` is 15 lines because `classify_player_archetype()` already had per-season cached frames. Most of the work was Pydantic and React.
- **Spec-first wasn't needed for these five.** Sprint 67's three-pass spec discipline saved real rework on a green-field surface, but for follow-ons the existing spec was already the source of truth (especially §1.7's team-fit penalty math). Item 2 implementation was a near-direct translation. Don't re-spec what's already spec'd.

---

## Workflow Lessons

- **A failing test that asserts the wrong invariant is worse than no test.** Round 1 of the team-fit ranking test asserted that the penalty would *flip* rankings (move differentiator ahead of duplicator). The 0.4× multiplier softens, doesn't invert — the test was wrong, not the service. Rewrote to assert what the penalty actually guarantees: the rankings differ from season mode. Lesson: when a test fails, ask whether the assertion matches the spec, not whether the code matches the assertion.
- **`source=...` URL parameters as inbound banner triggers continue to scale well.** Sprint 65 introduced the pattern, Sprint 67 extended it through the brief, Sprint 68 added a third deep-link path with no new infrastructure. Cheap convention, high reuse.
- **One-line copy changes in production-facing strings are worth the diff churn.** "Mid-range dependency" sounded clinical; "Mid-range heavy" reads like a coach saying it out loud. The polish pass adds nothing functionally but shifts the product's voice meaningfully.

---

## Technical Lessons

- **Test fixture helpers need to distinguish "new player" from "new season for existing player."** The Sprint-67 archetype test file's `_add_player()` always inserted a Player row. That worked for single-season fixtures but UNIQUE-violated when the evolution-timeline test added the same subject across three seasons. Added a sibling `_stat_row()` helper that only adds `SeasonStat`. Cleaner separation; future multi-season tests can reuse it.
- **Distance-layer penalties are easier to reason about than pool-layer filtering.** The team-fit spec could have been "exclude same-team teammates from the candidate pool" — but that would have changed the comp set rather than reweighting it, and it would have been hard to combine with future modes. Penalizing at the distance layer keeps the candidate pool consistent across modes and the mode's effect is fully explainable as "feature X mattered less to similarity for this subject."
- **Round-trip precision matters more than internal precision.** The Sprint-67 `usg_pct` bug wasn't that the data was wrong — it was that a `round(x, 1)` at the response-construction layer threw away precision the database had. Service-layer rounding should default to whatever precision the consumer needs; rounding for "cleanliness" is premature optimization that becomes a bug when a new consumer wants more precision.

---

## Next-Sprint Seeds

Cleared the explicit Sprint-67 follow-on backlog. The natural next sprints from the Sprint-67 closeout's "Next-Sprint Seeds" section remain:

- **Lineup Fit & Duo Chemistry** — archetype labels are now multi-season-aware (Sprint 68) and team-fit-aware (Sprint 68); next is teammate-pair compatibility scoring.
- **Printable Scouting Report** — reuse the Sprint-66 packet markdown export pipeline; the brief content already exists and is now coach-ready (Sprint 68 polish).
- **Team-vs-team archetype matchup matrix** — team X-Ray archetypes × player archetypes, with the player archetypes now historically grounded.
- **Team-Fit Explanation pill** noted in Deferred above is the smallest natural follow-on to Sprint 68 itself.
