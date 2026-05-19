# Golden-facts canary

A short list of true statements about real-world basketball that production
must agree with. A GitHub Action runs every day at 08:00 UTC, curls the
production API, and asserts every fact. Failures open a 🚨 issue.

The canary exists because the platform's automated tests can't catch
contract mismatches across the backend/frontend boundary (the Anthony
Edwards PPG bug is the canonical example: backend returned playoff seasons
DESC, frontend assumed ASC, both files individually passed their tests).
A canary that asks "does the platform agree with reality?" is the cheapest
catch for that whole class of bug.

## Files

- `golden_facts.yaml` — the fact list.
- `check_golden_facts.py` — the runner. Pure stdlib + pyyaml + jq.
- `../.github/workflows/golden-facts.yml` — daily cron + issue management.

## Running locally

```bash
pip install pyyaml
brew install jq      # or apt-get install jq on Linux
python qa/check_golden_facts.py
```

Run against a local backend:

```bash
BASE_URL=http://localhost:8000 python qa/check_golden_facts.py
```

## Adding a fact

When you fix a regression a user reported, add a fact that would have
caught it. Example: someone reports "Edwards' PPG is wrong" → after fixing,
add a fact pinning his PPG range.

Schema:

```yaml
- id: kebab-case-unique-key
  description: One-line human description
  endpoint: /api/path/under/api.courtvue.app
  jq_filter: 'a jq expression run against the response'
  operator: equals | in_range | min_length | contains_all | contains_none | ascending | descending
  value: depends on operator    # omit for ascending/descending
  source: where the ground truth lives — URL or file:line
  review_by: 2027-01-01         # forces a freshness check; stale dates surface as warnings
```

### Operators

| Operator        | `value` shape           | Behavior                                                |
|-----------------|-------------------------|---------------------------------------------------------|
| `equals`        | scalar                  | jq output == value                                      |
| `in_range`      | `[min, max]`            | min <= jq output as float <= max                        |
| `min_length`    | integer                 | len(jq output) >= value                                 |
| `contains_all`  | list                    | every list item appears in jq output (list)             |
| `contains_none` | list                    | no list item appears in jq output (list)                |
| `ascending`     | (no value)              | jq output is a non-decreasing list                      |
| `descending`    | (no value)              | jq output is a non-increasing list                      |

### Picking a good fact

- **Specific:** pin a value, not a fuzzy concept ("Edwards PPG is around 27" → range 27.0–28.0, not "is reasonable").
- **Stable:** prefer historical facts (2017 draft pick #3 = Tatum) over volatile ones (this week's MVP race leader).
- **One contract per fact:** "playoff_seasons is DESC" is one fact. "Edwards 2024-25 PPG is in [27, 28]" is another. Don't bundle.
- **Always include `source`:** future-you needs to know how to verify the truth changed (vs. the platform broke).

## Updating a fact

Two reasons to update:

1. **Truth changed.** New NBA season, new draft class, player retired, team relocated. Update `value` and bump `review_by`.
2. **Endpoint contract changed.** Field renamed, response shape moved. Update `jq_filter`.

Search for `review_by` dates that have passed — those are due for a refresh
(canary surfaces them as warnings, not failures).

## What to do when the canary fails

The GitHub Action will open a single issue titled "🚨 Golden-facts canary
failure" with the failing facts listed. Triage:

1. **Real regression** → fix the underlying bug, deploy, watch the next run.
2. **Underlying truth changed** → update `golden_facts.yaml`, push, watch.
3. **Endpoint URL changed** → update `endpoint` field on affected facts.

The issue auto-closes when the canary passes again.

## What this catches vs misses

**Catches:**
- Stale syncs (Edwards 2024-25 row never updated → PPG drifts out of range).
- Ordering / dedup bugs (playoff_seasons returns ASC when contract says DESC).
- Fabricated data re-appearing (Sprint 78 placeholder names sneak back into prod).
- Endpoint structure regressions (renamed field, missing array element).
- Auth / CORS / deploy breakage (any 4xx/5xx from a fact endpoint).

**Misses:**
- Cosmetic UI bugs that don't affect API output (chart color, button text, layout).
- Compute correctness inside the platform that no external truth exists for
  (proprietary score formulas, team-fit weightings).
- Slow drift (a stat that's wrong by 5% — won't trip an `in_range` band).

For UI-only regressions, a future iteration could add screenshot-based
visual regression. For now the canary catches the API-level class of bugs,
which is where the Edwards-style and draft-prospect-style failures live.

---

# Slop review

A second layer that runs *before* merge, not after. The canary catches things that ship; slop-review catches things before they ship.

## Two ways to invoke

**1. Manually via the `/slop-review` Claude Code skill** (local).
The skill at `.claude/commands/slop-review.md` walks 11 checkpoints against the current branch diff. Has access to bash for grepping consumers, checking test files, etc. Use for ad-hoc reviews or during sprint-closeout.

**2. Automatically via GitHub Action** (every PR).
`.github/workflows/slop-review.yml` runs `qa/run_slop_review.py` on every non-draft PR. Calls the Anthropic API with the canonical prompt in `qa/slop-review-prompt.md`, posts a sticky comment on the PR. Updates the same comment on subsequent pushes.

The two prompts are intentionally near-identical but adapted: the local skill uses bash (`grep`, `gh pr diff`), the API version receives the diff as context since it can't shell out.

## Setup for the GitHub Action

One-time, manual:

1. Generate an Anthropic API key at https://console.anthropic.com.
2. Add it to the repo: Settings → Secrets and variables → Actions → New repository secret. Name: `ANTHROPIC_API_KEY`.
3. Push any PR — the action runs automatically and posts a comment.

Cost: ~$0.04/PR using `claude-sonnet-4-6` with prompt caching on the system prompt. Adjust via `SLOP_REVIEW_MODEL` env var if you want haiku (cheaper, less rigorous) or opus (more rigorous, ~3x cost).

## What gets sent to the API

- The PR diff (`gh pr diff <N>`), truncated at 80KB.
- The changed-file list.
- The commit messages.

Anything else in the repo stays local. Production `DATABASE_URL`, `/etc/bip/env`, and other secrets are not in the repo so they cannot be sent.

## When to update the prompt

When you fix a new class of bug, add a checkpoint to both:
- `.claude/commands/slop-review.md` (local skill, bash version)
- `qa/slop-review-prompt.md` (API version, context-only)

The two files have a "keep in sync" note at the top. They will drift over time — that's fine as long as the checkpoint *list* stays parallel. The wording of each checkpoint can be optimized for its execution context.

## What this catches that the canary doesn't

The canary asks "does the platform agree with reality?" — it catches output errors after they ship. Slop-review asks "does this diff follow CourtVue's known rules?" — it catches *patterns* that produce output errors, before they ship. Different layers, different failure modes:

| Failure mode | Canary | Slop-review |
|---|---|---|
| Stale sync (Edwards 2024-25 row never updated) | ✅ | ❌ |
| Backend ordering contract drift | ✅ (post-deploy) | ✅ (pre-merge) |
| Fabricated seed data | ✅ | ✅ |
| New endpoint without frontend types | ❌ | ✅ |
| Direct DB writes in routers | ❌ | ✅ |
| Schema change without migration | ❌ | ✅ |
| Live nba_api outside the wrapper | ❌ | ✅ |
| Cosmetic UI bug | ❌ | ❌ |

