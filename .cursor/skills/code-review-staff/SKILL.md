---
name: code-review-staff
description: >
  Staff-engineer review for vocab-coach. Use when user asks for code review,
  production readiness, Google style, DRY/SOLID, or "review the code".
---

# Staff review checklist

## Order

1. Correctness / security bugs first
2. Idempotency and cost (extra LLM calls, duplicate events)
3. Authz gaps (resource id from wrong conversation)
4. DRY between `/api` and HTML routes
5. Style (ruff, TS build) last

## Must verify

- [ ] GET paths that trigger LLMs are idempotent
- [ ] `user_id` filter on every user-data query
- [ ] `authorize()` before mutate/delete
- [ ] Prompt files: new version only if already used
- [ ] FakeLLM coverage for new LLM paths
- [ ] React effects clean up streams
- [ ] No secrets in diff

## Output format

1. **Blockers** (fix now)
2. **Majors** (same PR if cheap)
3. **Nits** (optional)
4. **Out of scope** (do not boil ocean)

Then implement blockers unless user asked review-only.
