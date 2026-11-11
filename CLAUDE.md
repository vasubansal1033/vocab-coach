## Project

vocab-coach is a FastAPI web app that helps a user replace vague English words with precise ones, through AI conversation with word-choice feedback and through rewrite drills. It is a personal tool now and is built so it can become a multi-user product later.

- Design and reasoning: `docs/DESIGN.md`
- Build order and current progress: `docs/PLAN.md` (checkboxes show what is done)
- Product decisions, order of work and checklists for the planned sections: `docs/HANDOVER.md`

Work on one section of `docs/PLAN.md` at a time. Before writing code for a section, read the design sections it names, propose a plan, and wait for approval. Do not build features from later sections.

## Commands

```bash
uv sync --locked                        # install exactly what uv.lock pins
uv run uvicorn vocab.main:app --reload  # run the app on http://localhost:8000
uv run pytest                           # unit tests (no real LLM calls)
RUN_LLM_TESTS=1 uv run pytest -m llm    # tests that call the configured models
uv run ruff check . && uv run ruff format --check .
uv run alembic revision --autogenerate -m "<message>"
uv run alembic upgrade head
uv run vocab setup-nlp                  # spaCy model and WordNet data
# Lexicon seed: POST /api/lexicon/import/builtin (admin)
uv run vocab eval editor                # editor quality eval
docker compose -f infra/authentik/compose.yml up -d   # authentik on http://localhost:9000
```

## Layout

```text
src/vocab/
  main.py  config.py  db.py  events.py  cli.py
  auth/          OIDC login, identities, current_user, authorize()
  llm/           litellm + LangGraph only here; roles, graphs, prompts, logging
  prompts/       <role>.v<N>.md prompt files, never edited after use
  nlp/           spaCy analyzer, candidate spans, learned-word matching
  lexicon/       precision groups, drafting, review queue
  editor/        message -> suggestions
  conversation/  conversations, messages, partner stream, chat pages
  practice/      FSRS cards, due words, usage detection
  drills/        rewrite drill generation and grading
  metrics/       dashboard queries, MTLD
  web/templates/ web/static/vendor/
data/crutch_words.yaml
evals/editor_gold.yaml  evals/results/
infra/authentik/
migrations/
tests/
```

## Rules

#### Data

- Every table holding a user's data has an indexed `user_id`. Every query on such a table filters by `user_id`.
- IDs are UUIDv4 strings generated in Python.
- Use SQLAlchemy only; no raw SQLite-specific SQL. Use the generic `JSON` type for JSON columns.
- Behaviour that metrics depend on is recorded through `record_event()` in `events.py`, with a Pydantic payload model per event type. Do not update counters in place.
- Every schema change is an Alembic migration. Keep `render_as_batch=True`.

#### Auth

- Routes get the user from the `current_user` dependency and check resource access with `authorize()`.
- Never add a setting or flag that skips authentication. Tests use `app.dependency_overrides`.
- Store only the internal `user_id` in the session, never tokens or the OIDC `sub`.

#### LLM calls

- Only `src/vocab/llm/` imports `litellm` or LangGraph. Other code calls `run_structured_role`, `run_partner_stream`, or the lower-level `complete` / `stream` helpers.
- LangGraph workflows in `llm/graphs.py` orchestrate roles; nodes still call `complete` / `stream`.
- Code refers to roles, never model names. Model names come from settings.
- A prompt file that has produced recorded data is never edited; create the next version instead.
- Every structured output has a Pydantic model and is validated. Do not trust character offsets from a model; locate text in the source string.
- Unit tests use `FakeLLM`. Tests that call real models are marked `@pytest.mark.llm`.

#### Dependencies

- Add packages with `uv add`, commit `uv.lock`, install with `uv sync --locked`.
- Do not upgrade packages unless asked. When asked, upgrade one package with `uv lock --upgrade-package <name>` and report the version change.
- Before relying on a library behaviour that may differ between versions, check it against the installed version and say what you checked.

#### Style

- Type hints everywhere; `ruff` clean.
- Small functions with docstrings that explain why, not what.
- User-facing text and documentation: plain sentences, no em dashes.

## Definition of done for a section

- The "Done when" checks in `docs/PLAN.md` pass, and you have run them, not only reasoned about them.
- `uv run pytest` and `uv run ruff check .` pass.
- New behaviour has tests.
- The section's checkboxes in `docs/PLAN.md` are ticked, and any design change is reflected in `docs/DESIGN.md` in the same commit.
