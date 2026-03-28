# [Feature Name]

> For end-of-sprint memory notes, use `CLOSEOUT_TEMPLATE.md` and name the file `sprint-{NN}-closeout.md`.

**From:** Claude | Codex
**To:** Claude | Codex
**Sprint:** N
**Status:** Draft | Ready | In Progress | Done
**Created:** YYYY-MM-DD

---

## What This Is

One paragraph. What does this feature do and why does it exist? Written for the receiving agent, who has no context from the writing agent's session.

---

## What Has Already Been Done

Bullet list. Anything the writing agent built that the receiving agent depends on. Include exact file paths and function/class names.

- `backend/db/models.py` — `ExampleModel` added (lines N–N)
- `backend/routers/example.py` — `GET /api/example/{id}` endpoint returns `{...}`

---

## What You Need to Build

Ordered list of discrete tasks.

1. **Task name** — one sentence description
   - Files to touch: `path/to/file.py`
   - Input: what data/API/model does this consume
   - Output: what does it produce (endpoint shape, DB rows, UI state)
   - Constraints: any platform rules (Python 3.8, no raw dicts from routes, SWR hooks only, etc.)

2. **Task name** — ...

---

## API Contract (if applicable)

If the writing agent is building an endpoint the receiving agent's frontend will consume, specify the exact request/response shape. This is the contract — neither agent changes it without updating this spec.

```
GET /api/example/{id}
Response:
{
  "id": int,
  "field": string | null
}
```

---

## Shared Files This Touches

| File | Claimed by in AGENTS.md | Change needed |
|------|-------------------------|---------------|
| `frontend/src/lib/types.ts` | [agent] | Add `ExampleInterface` |
| `frontend/src/lib/api.ts` | [agent] | Add `getExample()` function |

---

## Build Order

```
1. [First task] — must come first because...
2. [Second task] — depends on 1 because...
3. [Third task] — independent, can run in parallel with 2
```

---

## Verification

How to confirm the work is correct. Runnable commands or observable UI states.

- `GET /api/example/123` returns `{"id": 123, ...}`
- Page shows component with non-null values
- `SELECT COUNT(*) FROM example_table;` returns > 0 after running import

---

## Do Not Touch

Files or systems the receiving agent must leave alone, even if they seem relevant.

- `backend/services/some_service.py` — writing agent is mid-refactor on this
