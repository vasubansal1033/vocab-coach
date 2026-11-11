## Purpose of this handover

This file hands the next round of work to a coding agent that has not seen the conversation in which it was planned. It records the product decisions, the order of work, and the checks that apply to every section. The detailed design is in `docs/DESIGN.md`, and the per-section tasks, files and decisions are in `docs/PLAN.md`. This file does not repeat them.

Everything up to and including the "Idioms" section of `docs/PLAN.md` is built. Remaining work is "Product readiness (later)" items already marked done for the personal phase, plus live editor eval with `RUN_LLM_TESTS=1` for idiom-aware `editor.v5` vs v3 if you want committed result JSON files.

## Product decisions

The product owner made these decisions on 11 Nov 2026. Do not change them; if one seems wrong, stop and ask.

- **Target user.** A non-native English speaker who works in English and wants to write with more precise and richer vocabulary. Defaults, examples, presets and seed content are chosen for workplace writing: emails, chat messages, status updates and reviews.
- **Positioning.** The app is a writing coach. Do not add speech features: no voice input, no pronunciation, no timed replies. Do not describe the app as a speaking coach in user-facing text.
- **Scope of the new work.** Two improvement sections for existing features, then three new practice modes. Choose the word and Compare reuse the existing lexicon, and Idioms adds new content with limits against overuse. The reasons are in "Planned practice modes" in the design.
- **Left out on purpose.** A difficulty setting, streaks or other gamification, and the literary idiom tier before the everyday tier.

## Reading order

1. `CLAUDE.md`, for the working rules. They apply unchanged.
2. "Purpose and scope" and "Planned practice modes" in `docs/DESIGN.md`. The second one ends with "Planned tables, events and roles", which lists every schema change, event and role these sections add.
3. The section of `docs/PLAN.md` you are about to build, including its "Decisions already made" and "Files to change".

## Order of work and dependencies

Build the sections in this order, one at a time, and get the product owner's approval of your plan before writing code for each.

| Order | Section | Depends on | Why it is in this place |
|---|---|---|---|
| 1 | Conversation improvements | Nothing new | Improves the main loop that users already use. It also adds `conversations.allow_idioms`, which Idioms needs later |
| 2 | Drill improvements | Nothing new | Small changes to an existing feature |
| 3 | Choose the word | Nothing new | Creates the shared `exercises` tables and module that Compare and Idioms reuse |
| 4 | Word sets | Nothing new | Adds `kind` and `details` to the lexicon. Compare and Idioms need it |
| 5 | Compare | 3 and 4 | Uses `exercises` and confusable sets |
| 6 | Idioms | 1, 3, 4 and 5 | Uses `allow_idioms`, `exercises`, idiom sets, and a new version of `compare_gen` |

Sections 1 and 2 can be swapped. Do not start 5 or 6 before 3 and 4 are done and ticked.

## Checklists for changes that touch several files

These changes have to be made in several places, and missing one breaks something without a test failing straight away. Each one was checked against the code on 11 Nov 2026.

#### Adding a table that holds user data

- Indexed `user_id` column and a UUIDv4 string `id`, as `CLAUDE.md` requires.
- An Alembic migration created with `uv run alembic revision --autogenerate`, reviewed by hand, and run with `uv run alembic upgrade head`.
- `src/vocab/account/service.py`: add the table to `export_user()` and `delete_user()`. Both list tables one by one, so a new table is not covered on its own. Delete child rows before parent rows.
- `infra/postgres/rls.sql`: enable row-level security and add a policy, following the existing tables.
- Every query filters by `user_id`, and routes check access with `authorize()`.
- `docs/DESIGN.md` "Data model": add the table, and remove it from "Planned tables, events and roles".

#### Adding an event type

- A Pydantic payload model in `src/vocab/events.py`, and an entry in `PAYLOAD_MODELS`. `record_event()` raises `ValueError` for unknown types.
- The event table in "Data model" in the design.

#### Adding a source for card reviews

- `CardReviewedPayload.source` in `src/vocab/events.py`, and `Source` in `src/vocab/practice/srs.py`. Both are `Literal` types and must list the same values.

#### Adding an LLM role

- `src/vocab/llm/roles.py`: the `Role` literal, the `ROLES` tuple, and the mappings in both `model_for()` and `prompt_version_for()`.
- `src/vocab/config.py`: `llm_<role>_model` and `llm_<role>_prompt_version`.
- `.env.example`: the model line in every provider block and the prompt version line.
- `src/vocab/prompts/<role>.v1.md`.
- A Pydantic output model, used through `run_structured_role(..., output_model=...)`.
- Unit tests use `FakeLLM`. Add one `@pytest.mark.llm` test that runs the real model.

#### Changing a prompt

- Never edit a prompt file that has produced recorded data. Create the next version and change the default version in `config.py` and `.env.example`.
- When the output schema changes with the version, the service picks the output model by the active version, so rows created with the old version still load.

#### Adding a frontend page

- The route in `frontend/src/App.tsx`, the API calls in `frontend/src/api.ts`, and a nav link where the section says so.
- `npm run build` in `frontend/` must pass. It runs `tsc -b`, so type errors fail the build.

## Traps found while planning

- **Flow mode and the "prompted" rule.** `suggestion_shown` is recorded inside `editor/service.py` when the editor runs. If the editor ran during a flow-mode conversation, the hidden suggestions would count as seen, and later uses of those words would be marked as prompted. That is why flow mode skips the editor until the recap.
- **Multi-word matching already works.** `nlp/usage.py` `find_learned_words()` uses `PhraseMatcher(attr="LEMMA")`, so "cutting corners" matches "cut corners". Write tests before changing anything there.
- **Queries on `PrecisionGroup`.** Five modules query it: `editor/service.py`, `drills/select.py`, `drills/service.py`, `metrics/queries.py` and `lexicon/service.py`. After the Word sets section, check each query for a `kind` filter, or confusable sets will leak into the editor and the rewrite drills.
- **SQLite migrations.** Making `head_lemma` nullable changes a column, which SQLite only supports through Alembic batch mode. `render_as_batch=True` is already set in `migrations/env.py`; keep it.
- **Answers in the browser.** `exercises.answer` must never be in a response before the attempt is submitted, or the answer can be read in the browser's developer tools.

## Definition of done

The definition in `CLAUDE.md` applies to every section. For these sections it also includes:

- `npm run build` passes whenever the frontend changed.
- Every row in "Planned tables, events and roles" that the section built has moved into "Data model" in the design.
- The section's checkboxes in `docs/PLAN.md` are ticked in the same commit as the code.

## What you see and what is causing it

| What you see | What is causing it |
|---|---|
| `ValueError: unknown event type` | The payload model was not added to `PAYLOAD_MODELS` in `events.py` |
| `ValueError: LLM_<ROLE>_MODEL is not configured` | The role was added to `roles.py` but the model is not set in `.env`, or the `.env.example` line was missed |
| Account deletion fails with a foreign key error | A new user table was not added to `delete_user()` in `account/service.py`, or child rows are deleted after their parent |
| Confusable words appear as editor suggestions or in rewrite drills | A query on `PrecisionGroup` is missing the `kind` filter |
| A word the user never saw is counted as prompted | The editor ran during a flow-mode conversation and recorded `suggestion_shown` |
| Old drills fail to load after the drill_gen v2 change | The service used the v2 output model for v1 rows instead of choosing by version |
| `npm run build` fails but the page works with `npm run dev` | Type errors; the dev server does not type-check, the build does |
