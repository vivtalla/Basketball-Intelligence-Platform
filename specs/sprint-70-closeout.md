# Sprint 70 Closeout — Design System Integration

**Date:** 2026-04-27
**Branch:** `feature/sprint-70-design-system-integration`
**Status:** Implementation complete; ready for merge to `master`

---

## Goal

Bring the CourtVue Labs design system (cream/forest-green/gold palette, Source Serif 4 display, Source Sans 3 sans, JetBrains Mono mono) deeper into the product surfaces. Sprint 70 carried the design language into pages where existing functionality was already rich but the visual chrome had drifted from the design specs delivered as gzipped tarball at `https://api.anthropic.com/v1/design/h/cs_JsS8pYIm1mYPQ8INqJQ`.

---

## Shipped

### Home page (already mostly aligned, plus polish)

- `<LiveTicker>` strip above nav with auto-scrolling demo scoreboard, hover-to-pause, and a CSS-keyframe live-pulse dot.
- `<FloatingBall>` decorative SVG basketballs in the hero, animated via `cv-ball-float` keyframe.
- `<SpotlightCursor>` mouse-following radial-gradient overlay inside the hero panel.
- `<Reveal>` IntersectionObserver-driven fade-up wrappers around platform cards (staggered) and below-fold sections.
- `<HomeLiveCourt>` composed section with `<LiveShotPulse>`, `<WinProbabilityChart>`, and `<StandingsLadder>` plus realistic demo data.

### Teams directory (`/teams`) — full redesign

- Replaced the simple grid of team cards with a two-column layout that mirrors the design's `TeamsScreen.jsx`.
- Conference filter pills (All / East / West) backed by a static `TEAM_META` map (conference + primary brand color keyed by abbreviation).
- Sort dropdown (Name / Conference / Roster size) with deterministic comparators.
- Sticky left directory: each `TeamRow` shows the colored abbreviation badge, team name, conference label, player count, and a left-border selection indicator in team color.
- Right `TeamDetailPreview` panel: color-tinted header card, four quick-access tab links (Intelligence / Roster / Shot lab / Splits), and a primary CTA to the full `/teams/[abbr]` dashboard.

### Metrics page (`/metrics`) — hero leader card

- Added a hero card above the existing composite leaderboard inside `CustomMetricBuilder.tsx`, only when `data.player_rankings.length > 0`.
- Renders `<HeroHardwood>` woodgrain texture as background, the metric label kicker, the #1 ranked player and their team, and the composite score in 72pt `bip-display` type.
- The 2×2 preset grid (Scoring Engine / Playmaking Load / Two-Way Impact / Efficiency Big) was already in place — verified.

### Pre-Read page (`/pre-read`) — three new sections

1. **Visual matchup header card** — appears when both team and opponent are selected. Two team boxes flanking a centered "vs" with team abbreviation badges, full team names, and home/away labels.
2. **MatchupBar bilateral bars** — six head-to-head metrics rendered inside the matchup card on a divider: OFF RTG, DEF RTG, PACE, EFG%, TS%, NET RTG. Fed by `useTeamAnalytics(home, season)` + `useTeamAnalytics(away, season)`. Winning side highlighted in forest-green, losing side muted.
3. **Focus levers section** — surfaces `data.focus_levers` from the existing Pre-Read deck API in the design's `FocusLever` card style: colored dot + colored kicker title + body summary + italic coaching prompt. Levers were already returned by `/api/pre-read/{team}/{opponent}` but not rendered on this page (only inside `TeamIntelligencePanel` and `TeamDecisionToolsPanel`).

### Compare page (`/compare`) — two new summary panels in `ComparisonView`

1. **"The deltas"** — a 5-card grid showing the largest stat differences between the two players (Scoring, True shooting, Playmaking, Rebounding, Impact BPM). Each card shows the leader's last name, "leads" label, and the delta value in display type. Color-coded so the leader's value is in `--accent`.
2. **"Key takeaways"** — top 3 plain-language bullet differences computed from absolute deltas across PTS, TS%, AST, REB, BPM, STL, BLK. Reads like "Tatum leads by 4.2."

Both panels render inside the `mode !== "percentile" && mode !== "arc"` block so they respect the existing view-mode toggle.

---

## Verification

- Frontend build: `npm run build` → **passed clean** (Turbopack 16.2.1, 17/17 pages).
- Frontend lint: `npm run lint` → 0 errors, 7 pre-existing `usePlayerStats.ts` warnings (unchanged from Sprint 69 baseline).
- Backend: untouched in this sprint. No new tests required; backend test count stays at **257 passing**.
- Live smoke: Teams directory toggling between East/West, selecting teams, and clicking through to `/teams/[abbr]`; Metrics hero card updates when sliders change; Pre-Read matchup bars render for OKC vs BOS in 2024-25; Compare deltas/takeaways update when switching between Career/Season/Percentile/Arc modes.
- `git diff --check` clean.

---

## Workflow lessons

- **Subagent fan-out hit the API rate limit.** I dispatched 4 parallel design-implementation subagents (Ask+Home, MVP+Metrics, Teams+Compare, Player+Pre-Read) with detailed per-page briefs. The first agent (Teams+Compare) and Player+Pre-Read agent both misrouted into "scan transcript files" tasks before consuming any tool calls. The retries plus the other two agents all returned `You've hit your limit · resets 4:50am (America/Los_Angeles)` after 14–19 tool calls. I had to fall back to inline implementation in the main session. Lesson: when the design touches 8 pages, single-stream inline implementation with focused gap-targeting is more reliable than parallel subagent fan-out, especially mid-conversation when the rate-limit budget is already partially spent.
- **The design's gap was thinner than the briefs implied.** AskWorkspace, MvpRacePanel, ComparisonView, and PlayerHeader were all already richer than the design's reference screens. Only Teams (full redesign), Metrics (hero card), Pre-Read (three sections), and Compare (deltas/takeaways) had concrete visual gaps that meaningfully changed the surface. Spending more time auditing pages page-by-page before generating subagent prompts would have surfaced this — but the rate-limit blast meant the audit work happened inline anyway.
- **Render existing API data before reaching for static demo data.** The Pre-Read focus-levers were returned by `/api/pre-read/{team}/{opponent}` but never wired to the page. Surfacing them was lower-cost than mocking demo content and immediately moved the page closer to the design.

---

## Deferred (moved to backlog)

These design elements were intentionally not added because the existing components are already richer than the design or because the cost-benefit didn't warrant the change in this sprint:

- **MVP candidate-card hardwood backgrounds and 5-pillar bars in `MvpRacePanel`.** The current panel has 6 value pillars + 5 award modifiers, an impact radar, clutch cards, and signature games — already richer than the design's `CandidateCard` + `PillarBar` combo.
- **Player page 6-column `PercentileBadge` row.** `PlayerHeader` already renders 6 percentile pills (PPG, RPG, APG, TS%, PER, BPM) with the same color-coded percentile band logic and ordinal display ("87th").
- **Compare PlayerCard hardwood headers with color-coded names + "Change player ▾" inline dropdown.** `PlayerAvatar` with the existing player slot search above already covers the same UX. Adding hardwood texture under the headers would compete visually with the bilateral percentile bars below.
- **Home league leaders TREND sparkline column.** Would require a new backend endpoint for per-leader rolling per-game series.

---

## Next-sprint seeds

- **Surface untapped API data.** The Pre-Read focus-levers find suggests there may be other API responses with payload that's never rendered on the page that owns it. A short audit pass over the `/api/pre-read`, `/api/mvp/*`, and `/api/team-fit` payloads vs. their consumer pages could yield more "free" UI wins.
- **Design-system component library.** Now that `HeroHardwood`, `Reveal`, `LiveTicker`, `FloatingBall`, `SpotlightCursor`, `Parallax`, `LiveShotPulse`, `StandingsLadder`, and `WinProbabilityChart` exist as primitives, a single page consolidating them with prop docs would speed up any future design-driven sprint.
- **Print/PDF deck for Pre-Read.** Pre-Read already has `window.print()` and `print:hidden` utilities; the matchup header + matchup bars + focus levers section now read like a print-friendly pregame deck. A dedicated print stylesheet pass could turn this into a coach-handoff artifact.

---

## Files changed

```
frontend/src/app/teams/page.tsx                 (full rewrite — 261 ins / 109 del)
frontend/src/app/pre-read/page.tsx              (matchup card + bars + focus levers — ~165 ins)
frontend/src/components/CustomMetricBuilder.tsx (hero leader card — 38 ins)
frontend/src/components/ComparisonView.tsx      (deltas + takeaways panels — ~100 ins)
AGENTS.md                                       (sprint status update only)
```

Plus the home/layout/component additions from session 0 (LiveTicker, Reveal, FloatingBall, SpotlightCursor, Parallax, LiveShotPulse, StandingsLadder, WinProbabilityChart, HomeLiveCourt) which were committed earlier in the session before the sprint branch was formalized.

---

## Commits (sprint branch)

```
4d68672 feat: render Pre-Read focus levers in design's three-card layout
9b7fe62 feat: add Compare deltas/takeaways panels and Pre-Read matchup bars
66c1abe feat: implement design system UI elements across Teams, Metrics, and Pre-Read pages
a024b80 docs: update Claude status in AGENTS.md — Sprint 70 started
```
