---
name: eng-team
description: >
  Engineering-manager orchestration for vocab-coach PLAN sections after
  docs/HANDOVER.md. Use when user asks to staff a team, run leads/devs/QA,
  or execute the planned practice-mode sections without waiting for approval.
---

# Eng team (vocab-coach)

Product owner decisions in `docs/HANDOVER.md` are fixed. Do not reopen them.

## Roster

| Role | Skill / duty |
|---|---|
| EM (this skill) | Order of work, gates, atomic commits, no scope creep |
| Backend lead | Schema, services, API, migrations, events, FakeLLM tests |
| Frontend lead | SPA pages, `api.ts`, nav, `npm run build` |
| QA lead | Done-when checks, pytest, ruff, SPA build, PLAN ticks |
| Staff review | `.cursor/skills/staff-review-refactor/SKILL.md` after a section batch |

Legacy QA loop stays available: `.cursor/skills/agent-team/SKILL.md`.

## Order (do not skip dependencies)

1. Conversation improvements  
2. Drill improvements (may run parallel with 1)  
3. Choose the word  
4. Word sets (may run parallel with 3)  
5. Compare (needs 3 + 4)  
6. Idioms (needs 1 + 3 + 4 + 5)

## Section protocol

1. Read `CLAUDE.md`, `docs/HANDOVER.md`, named DESIGN slices, and the PLAN section.  
2. Implement Decisions already made as written. User said "don't ask" overrides HANDOVER "propose first" for this run.  
3. Follow multi-file checklists in HANDOVER (tables, events, roles, prompts, frontend).  
4. Tick PLAN checkboxes and move DESIGN planned rows into Data model in the same commit.  
5. Gate: `uv run pytest`, `uv run ruff check .`, and `npm run build` in `frontend/` when UI changed.  
6. One atomic commit per section (or smaller atomic commits inside a section if clearer).

## Prompt template for a builder agent

```text
Repo: /Users/vasubansal/projects/ai-vocab
You are the <backend|frontend|full-stack> builder for section "<NAME>".
Do not ask questions. Implement the section fully.
Read CLAUDE.md, docs/HANDOVER.md, and the PLAN section "<NAME>".
Decisions already made are fixed. Tick PLAN checkboxes when Done when passes.
Update docs/DESIGN.md as HANDOVER requires. Run pytest + ruff (+ npm build if FE).
Return: files changed, tests run, remaining risks.
```
