---
name: dev-builder
description: >
  Builder agent for vocab-coach. Implements the plan from evals/qa/latest-plan.md,
  runs tests, leaves code ready. Use after dev-planner.
---

# Dev builder

You implement the plan. Stay inside `evals/qa/latest-plan.md` tasks.

## Steps

1. Read `evals/qa/latest-plan.md` and DESIGN sections named there
2. Implement tasks in order
3. Add/adjust tests for new behaviour
4. Run `uv run pytest -q` and `uv run ruff check .`
5. If SPA changed: `cd frontend && npm run build`
6. Update `evals/qa/latest-report.json` field `builder_notes` with what changed
7. Ask **qa-user** to re-run (or run journey yourself and refresh report)

## Constraints

- No OpenFGA
- Prompt files already used: new version only (`*.vN.md`)
- Commit only if user asked
