## Sprint 18: Hardwood Editorial Refresh

Status: Ready for Engineer

### Goal

Refresh the platform visual system around the selected `Hardwood Editorial` direction so the product feels more premium, basketball-native, and distinct from generic analytics dashboards.

### Design direction

Core palette:

- warm cream background
- charcoal primary text
- deep forest primary accent
- brass secondary accent

Mood:

- premium scouting notebook
- hardwood / film-room energy
- editorial rather than generic SaaS

### Initial implementation scope

Prioritize the most visible shared surfaces first:

- global theme tokens in `frontend/src/app/globals.css`
- app shell and nav in `frontend/src/app/layout.tsx`
- homepage in `frontend/src/app/page.tsx`
- primary search surfaces:
  - `frontend/src/components/NavSearch.tsx`
  - `frontend/src/components/PlayerSearchBar.tsx`
- homepage support surfaces:
  - `frontend/src/components/FavoritesList.tsx`
  - `frontend/src/components/HomeLeagueLeaders.tsx`
- page entry shells:
  - `frontend/src/app/players/[playerId]/page.tsx`
  - `frontend/src/app/teams/[abbr]/page.tsx`
- player header:
  - `frontend/src/components/PlayerHeader.tsx`

### Rules

- preserve current product structure and functionality
- do not add schema or API changes
- use shared CSS variables so the palette is reusable in follow-up sprints
- avoid reintroducing generic blue-first styling where the new palette should own the hierarchy
- keep contrast readable on desktop and mobile

### Acceptance checks

- home page clearly reads as Hardwood Editorial rather than the prior default gray/blue look
- nav, search, cards, buttons, and key shells all use the same visual system
- player and team entry surfaces feel visually consistent with the new palette
- frontend still passes lint and build

### Expanded rollout

The sprint now extends beyond the first shared-surface pass and should reach the full analyst workflow:

- all top-level app pages should reflect the Hardwood Editorial palette
- shared data panels and tables should move off generic white/blue/gray defaults
- text hierarchy should pop within the new system:
  - charcoal for primary reading
  - deeper forest for key interactive emphasis
  - brass for section kickers and attention states
  - stronger green/red tones only for meaning, not base hierarchy
- loading, empty, and limited states should still feel native to the same visual language
