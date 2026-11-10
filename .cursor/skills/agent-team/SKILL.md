---
name: agent-team
description: >
  Orchestrate vocab-coach agent team: QA user finds bugs, planner designs fixes,
  builder implements. Use when user asks for agent team, QA+dev loop, or
  "plan and solve" after QA.
---

# Agent team (vocab-coach)

Run in order. Do not skip QA before planning.

## Roles

1. **qa-user** — acts as signed-in learner; hits `/api` (and SPA pages if needed); writes `evals/qa/latest-report.json`
2. **dev-planner** — reads QA report + DESIGN/PLAN; writes `evals/qa/latest-plan.md`
3. **dev-builder** — implements plan; runs pytest + ruff; updates report status

## Invoke

User says: "run agent team", "QA then fix", "plan and solve", or `@agent-team`.

1. Follow `.cursor/skills/qa-user/SKILL.md` first
2. Then `.cursor/skills/dev-planner/SKILL.md` (only if report `status` is `fail`)
3. Then `.cursor/skills/dev-builder/SKILL.md`
4. Re-run qa-user until report has `status: pass` or user stops

Quick smoke without full loop:

```bash
uv run pytest tests/e2e/test_qa_user_journey.py -q
# writes evals/qa/latest-report.json
```

## Rules

- No OpenFGA work (out of scope)
- Only `vocab.llm` imports litellm/LangGraph
- FakeLLM for unit/e2e without `RUN_LLM_TESTS=1`
- One PLAN-sized change set at a time when building product features
- Caveman OK in chat; code/commits normal prose
