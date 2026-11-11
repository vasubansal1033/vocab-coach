---
name: staff-review-refactor
description: >
  Staff-engineer review, Google-style refactor, and redundant-code removal for
  vocab-coach. Use when user says staff review, review-refactor, remove redundant,
  Google style pass, production readiness cleanup, or invokes /staff-review-refactor
  or @staff-review-refactor.
---

# Staff review → refactor → remove redundant

Run this skill end to end unless user says **review-only**.

## Style bar

- **Python**: Google Python Style Guide spirit + project Ruff (`line-length=100`, `E,F,I,UP,B,ANN`). Type hints everywhere. Docstrings explain why.
- **TypeScript/React**: Clear names, no unused imports, effects clean up subscriptions, API only via `frontend/src/api.ts`.
- Follow `.cursor/rules/code-conventions.mdc`, `python-google-style.mdc`, `frontend-ts.mdc`.

## Phase 1 — Review (read only)

Scan hot paths first:

- `src/vocab/api/`, `conversation/`, `editor/`, `account/`, `llm/`
- `frontend/src/`
- Recent diffs / uncommitted work when present

Prioritize findings:

1. **Blockers** — correctness, authz, data loss, extra LLM cost, broken UX
2. **Majors** — DRY/SOLID violations cheap to fix; dead code; duplicate routes
3. **Nits** — naming, import order (let ruff fix)
4. **Out of scope** — boil-the-ocean rewrites, unrelated features

### Must-check list

- [ ] Idempotent GET feedback (no re-LLM / duplicate `suggestion_shown`)
- [ ] `user_id` filter on user-data queries; `authorize()` before mutate/delete
- [ ] No dual ownership of the same UI (SPA vs dead Jinja pages)
- [ ] Shared logic in one service (not copied across `/api` and HTML)
- [ ] Prompt files: never edit shipped versions; bump `vN`
- [ ] FakeLLM tests for new LLM paths; React stream cleanup
- [ ] No secrets in tree

Print a short report in that 4-bucket format, then continue to Phase 2.

## Phase 2 — Refactor + delete

For each Blocker and cheap Major:

1. Prefer **delete** dead code over commenting it out
2. Extract shared helpers once (SOLID: single owner module)
3. Keep public `/api` contracts stable unless intentionally versioning
4. Do not invent features; do not expand scope past findings
5. Touch Jinja only if still serving users (about/admin) or delete unused templates

### Safe deletes (when SPA owns UI)

- Orphan templates under `web/templates/conversation|dashboard|drills|practice` if routes only redirect
- Unused CSS / imports / duplicate API helpers
- Redundant HTML POST handlers superseded by `/api`

### Do not delete

- Alembic migrations, prompt files that produced recorded data, FakeLLM fixtures still referenced
- About/privacy/attribution and lexicon admin unless user asks

## Phase 3 — Verify

```bash
uv run ruff check .
uv run pytest -q
# if frontend changed:
cd frontend && npm run build
```

Fix failures from this pass. Summarize: what removed, what refactored, what left Out of scope.

## Invoke phrases

User may say any of:

- `/staff-review-refactor`
- `staff review refactor`
- `remove redundant code`
- `Google style cleanup`

Treat all as full run (review + implement + verify) unless they add **review-only**.
