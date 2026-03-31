# Product Backlog

Living list of product, workflow, and platform ideas that are worth revisiting.

Use this file for:
- sprint seeds that should survive beyond one closeout note
- feature ideas that are promising but not yet scheduled
- cleanup or platform improvements that matter, but are not urgent

Guidelines:
- keep entries short and concrete
- group by theme rather than by date
- move shipped items into sprint specs/closeouts instead of leaving them here

---

## Analyst Workflows

- Metrics-to-analysis handoff:
  Let an analyst take a custom metric result straight into compare, player pages, team pages, or a prefilled watchlist without re-entering context.
- Persistent analyst state:
  Decide whether saved metric state should stay URL-based or move toward account-backed sync, named workspaces, and reusable analyst libraries.
- Next flagship decision board:
  Build another deep workflow that answers a real analyst question end to end instead of adding another broad stats surface.
- Guided game follow-through:
  Turn player and team signals into clearer “watch this next” paths that drop the user into the right Game Explorer context with a reason attached.

## Near-Term Candidate Ideas

- Compare workspace 2.0:
  Make Compare feel less like a static side-by-side and more like an investigation surface with better context, matchup framing, and metric carryover.
- Metric collections:
  Add curated public metric sets such as scoring, playmaking, lineup-fit, or prospect-style templates that feel editorial rather than generic.
- Analyst notebook layer:
  Explore lightweight notes, saved lists, or session state so users can keep track of what they were investigating across pages.
- CourtVue Labs onboarding:
  Add a clearer first-run path that explains what each workspace is for and how an analyst should move between them.

## Metrics and Modeling

- Expand custom metric presets beyond the current starter set with more role- and question-specific templates.
- Add shareable metric libraries or curated public templates that can be browsed, loaded, and adapted.
- Support more advanced metric controls, like grouped components, alternate weighting views, inverse defaults, or normalization hints.
- Decide whether the internal `CourtVueMetric*` frontend types should be normalized or left as-is after the public product naming change.

## Player and Team Surfaces

- Modernize the `Player Stats` workspace styling so it matches the newer editorial surfaces more closely.
- Add richer follow-through from player trend and team rotation panels into compare and game workflows.
- Continue improving visible naming, labeling, and analyst-oriented summaries across high-traffic pages.
- Build tighter links between player pages, team pages, and standings so context carries across the platform instead of resetting on each page.

## Platform and Brand

- Continue the `CourtVue Labs` rename sweep anywhere legacy naming still survives in docs, specs, repo metadata, or GitHub settings.
- Decide whether to rename internal type and helper names, or keep the product rename user-facing only.
- Add a lightweight brand/style guide for CourtVue Labs voice, copy, and UI usage.
- Define the product story more clearly:
  what CourtVue Labs is, who it is for, and how it differs from a generic stats dashboard.

## Data and Operations

- Strengthen warehouse visibility with clearer health snapshots, backlog monitoring, and worker-status surfaces.
- Add more operational runbooks where warehouse recovery steps are still tribal knowledge.
- Identify the next highest-value data coverage improvement after the current 2025-26 backfill work.
- Surface data-readiness more cleanly to the product layer so analysts know when a workflow is fully trustworthy versus partially covered.
