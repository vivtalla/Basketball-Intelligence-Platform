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
