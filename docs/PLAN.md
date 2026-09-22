## How to use this plan

The plan is split into sections that each end in something you can run and check. Work through them in order, one section per Claude Code session or a few sessions, and commit at the end of each. The design behind every decision is in `docs/DESIGN.md`; this file says what to build and in which order, and points to the design section that explains each part.

A working loop that suits Claude Code:

1. Start a session in the repo root. Claude Code reads `CLAUDE.md` automatically.
2. Paste the "Prompt for Claude Code" from the section you are on. Each prompt asks Claude Code to read the relevant design sections and propose a plan before writing code, so you can correct it early.
3. Review the proposed plan, then let it implement.
4. Run the checks under "Done when" yourself, not only the ones Claude Code reports.
5. Tick the boxes in this file and commit.

Sections marked as later are for the product phase and can wait.

## Foundation

#### Goal

A running FastAPI app with settings, a database, migrations, tests and linting, and nothing else.

#### Tasks

- [x] Create the project with `uv init --package vocab-coach` and a `src/vocab/` layout. Python 3.13.
- [x] Add dependencies with `uv add`: `fastapi`, `uvicorn[standard]`, `jinja2`, `pydantic-settings`, `sqlalchemy`, `alembic`, `sse-starlette`, `authlib`, `itsdangerous`, `httpx`, `litellm`, `spacy`, `nltk`, `wordfreq`, `fsrs`, `pyyaml`. Dev group: `pytest`, `pytest-asyncio`, `ruff`.
- [x] Commit `uv.lock`. Install only with `uv sync --locked` (see "Supply-chain precautions" in the design).
- [x] `config.py` with a `Settings` class (pydantic-settings) covering every variable in "Configuration", and `.env.example` with placeholder values.
- [x] `db.py` with the engine, a session dependency, and a `connect` event listener that sets `PRAGMA foreign_keys=ON` and `PRAGMA journal_mode=WAL`.
- [x] Alembic initialised in `migrations/` with `render_as_batch=True` in `env.py`, and the SQLAlchemy metadata wired in for autogenerate.
- [x] `main.py` with an app factory, a `/healthz` route, Jinja2 templates, and static files. Vendor `htmx.org` 2.0.11, `htmx-ext-sse` 2.2.4 and `chart.js` 4.6.1 into `src/vocab/web/static/vendor/`.
- [x] A base template with a header, a main area and a footer link to `/about/attribution`.
- [x] A `vocab` CLI entry point (Typer or `argparse`) for later commands.
- [x] `ruff` configured; `pytest` configured with an in-memory SQLite fixture.

#### Done when

- `uv run uvicorn vocab.main:app --reload` serves `/healthz` and the base page.
- `uv run pytest` passes, including a test that a foreign key violation raises an error (proves the pragma is on).
- `uv run alembic upgrade head` runs on an empty database.
- `uv run ruff check .` is clean.

#### Prompt for Claude Code

```text
Read CLAUDE.md and the sections "Stack", "Why SQLite now and what keeps Postgres possible",
"Configuration" and "Supply-chain precautions" in docs/DESIGN.md. Then implement the
"Foundation" section of docs/PLAN.md. Propose your file layout and plan first and wait for
my approval before writing code. Do not add any feature beyond that section.
```

## Login and users

#### Goal

You can sign up and log in through authentik, and every request knows the internal `user_id`.

#### Tasks

- [x] `infra/authentik/`: download the official `compose.yml`, generate `PG_PASS` and `AUTHENTIK_SECRET_KEY` into `infra/authentik/.env` (git-ignored), and document the setup steps in `infra/authentik/README.md`.
- [x] In authentik: create an OAuth2/OpenID provider and an application with slug `vocab-coach`, set the redirect URI to exactly `http://localhost:8000/auth/callback`, and enable an enrollment flow so new users can sign up. Record the steps in the README.
- [x] Models and migration for `users` and `identities` (see "Identity" in the design).
- [x] `auth/oidc.py`: Authlib `OAuth` registration, `/auth/login`, `/auth/callback`, `/auth/logout` (which also redirects to authentik's end-session endpoint).
- [x] `SessionMiddleware` with cookie name `vocab_session` and `SESSION_SECRET`.
- [x] On callback: find or create the user through `(issuer, subject)`, store only `user_id` in the session.
- [x] `auth/deps.py`: `current_user` dependency that redirects to login for pages and returns 401 for JSON or htmx requests.
- [x] `auth/authorize.py`: `authorize(user_id, action, resource)` that compares `resource.user_id` with the caller and raises 404 on mismatch (404 rather than 403, so other users' IDs are not confirmed to exist).
- [x] Test helpers that log in a fake user with `app.dependency_overrides`.

#### Done when

- Signing up through authentik creates one `users` row and one `identities` row; logging in again does not create more.
- Logging out of the app also ends the authentik session.
- A test proves user A gets 404 when requesting user B's resource.
- No code path skips `current_user` outside tests.

#### Prompt for Claude Code

```text
Read CLAUDE.md and "Authentication and authorization" and "Identity" in docs/DESIGN.md.
Implement the "Login and users" section of docs/PLAN.md. I will do the authentik admin
steps myself: write them as a checklist in infra/authentik/README.md first and wait for me
to confirm they are done before testing the login flow. Propose your plan first.
```

## Language analysis

#### Goal

Given a user message, the app counts lemmas and marks candidate vague spans, with no LLM involved.

#### Tasks

- [x] `uv run vocab setup-nlp` downloads `en_core_web_sm` and the NLTK `wordnet` corpus. Behind a proxy, NLTK 3.10.4 refuses to download unless `NLTK_ALLOW_PROXIED_URLOPEN=1` is set; the command should print that hint when the download fails.
- [x] `data/crutch_words.yaml`: an initial list of crutch lemmas with part of speech (for example `good ADJ`, `bad ADJ`, `big ADJ`, `really ADV`, `very ADV`, `thing NOUN`, `stuff NOUN`, `get VERB`, `make VERB`, `fix VERB`, `show VERB`, `say VERB`, `use VERB`, `lot NOUN`, `hard ADJ`, `easy ADJ`, `problem NOUN`).
- [x] `nlp/analyzer.py`: `analyze(text) -> Analysis` with `word_count`, lemma counts (lemma and surface form), and candidate spans. A span is a candidate when its lemma is in the crutch list, or when it is an adjective or adverb with Zipf frequency of 5.5 or more. Verbs are marked only through the crutch list. Include an intensifier before an adjective in the span (`really hard`, `very good`) and an adjective with its noun (`big problem`).
- [x] `nlp/usage.py`: `find_learned_words(analysis, learned_option_lemmas) -> list[Hit]`, using spaCy's `PhraseMatcher` on lemmas so multi-word options such as `work around` match `worked around`.
- [x] Load spaCy once at startup, not per request.
- [x] Persist `messages.word_count` and `message_lemma_counts` through a service function (tables come in the "Conversation UI" section; for now test the analyzer output only).

#### Done when

- For "Yeah the migration was really hard and we had a big problem with the old data, but we fixed it in the end." the analyzer marks `really hard`, `big problem` and `fixed`, and does not mark `migration`, `data` or `had`. It may also mark `old`. This is a unit test.
- For "We worked around it" with learned option `work around`, `find_learned_words` returns one hit.
- Analysing a 100-word message takes under 50 ms after warm-up on your machine (log it once; not a CI test).

#### Prompt for Claude Code

```text
Read CLAUDE.md and the steps "analyse" and "a later conversation" in "One message through
the system" in docs/DESIGN.md. Implement the "Language analysis" section of docs/PLAN.md,
test-first: write the unit tests from "Done when" before the analyzer. Propose your plan first.
```

## LLM client

#### Goal

One module through which every LLM call goes, by role, with versioned prompts, structured output, retries and logging.

#### Tasks

- [x] Model and migration for `llm_calls`.
- [x] `llm/prompts.py`: load `prompts/<role>.v<N>.md`, render with Jinja2, return text plus `prompt_id` and `prompt_version`. The active version per role comes from settings.
- [x] `llm/client.py`: `async def complete(role, variables, *, user_id=None, output_model=None)`. Resolve the role to a model string from settings. When `output_model` is given, use `litellm.supports_response_schema(...)` to choose between passing the Pydantic class and `{"type": "json_object"}` with the schema in the prompt. Validate with `model_validate_json`; retry once with the validation error; then fail.
- [x] `async def stream(role, variables, *, user_id=None)` for the partner, yielding text chunks.
- [x] Record every call in `llm_calls`: role, model, prompt id and version, tokens, cost (from LiteLLM's response when available), latency, status, error.
- [x] A `FakeLLM` for tests that returns fixtures by role, and an `@pytest.mark.llm` marker for real-model tests, skipped unless `RUN_LLM_TESTS=1`.
- [x] `uv run vocab llm ping <role>` that sends a tiny request to the configured model and prints the reply and latency.

#### Done when

- `vocab llm ping partner` works against Ollama and `vocab llm ping editor` works against your hosted model.
- A unit test proves that an invalid JSON reply triggers exactly one retry and then a recorded failure.
- A unit test proves the `json_object` fallback is used when schema support is reported as false.
- No module other than `llm/` imports `litellm` (add a test that scans imports).

#### Prompt for Claude Code

```text
Read CLAUDE.md and "LLM layer" in docs/DESIGN.md. Implement the "LLM client" section of
docs/PLAN.md. Check the installed LiteLLM version's behaviour for supports_response_schema
and mock_response yourself before relying on it, and tell me what you found.
Propose your plan first.
```

## Lexicon

#### Goal

Approved precision groups in the database, a way to draft more with an LLM, and a page to review them.

#### Tasks

- [x] Models and migration for `precision_groups`, `precision_options` and `review_queue`.
- [x] Write seed files in `data/precision_groups/` for at least ten head lemmas from the crutch list, in the format shown in "Precision groups". Review them yourself; these are the quality baseline.
- [x] `uv run vocab lexicon load` upserts YAML seeds as `approved`, keyed by group and option IDs, so rerunning is safe.
- [x] `prompts/group_gen.v1.md` and `uv run vocab lexicon draft <lemma>`: gives the LLM the WordNet senses for the lemma and asks for groups in the seed format, saved as `draft`.
- [x] `/admin/lexicon` page (restricted to an admin user ID from settings): lists drafts and review-queue items with approve, edit and reject.
- [x] `uv run vocab lexicon export` writes approved groups back to YAML, so the lexicon stays reviewable in git.

#### Done when

- `vocab lexicon load` twice in a row leaves the same row counts.
- `vocab lexicon draft fix` produces a `fix.repair` draft whose options you would mostly approve.
- Approving a draft makes it visible to a query for approved groups by lemma.

#### Prompt for Claude Code

```text
Read CLAUDE.md and "Precision groups" and "Lexicon (shared reference data)" in
docs/DESIGN.md. Implement the "Lexicon" section of docs/PLAN.md. For the seed files, draft
ten head lemmas and show them to me for review before loading them. Propose your plan first.
```

## Editor and its eval

#### Goal

The editor turns a message into at most two good suggestions, and you can measure editor quality before building UI on top of it.

#### Tasks

- [x] `prompts/editor.v1.md` implementing every rule in "Editor contract".
- [x] Pydantic models from "Output schema" in `editor/schemas.py`.
- [x] `editor/service.py`: `analyze_message(message) -> list[Suggestion]` that runs the analyzer, loads candidate groups, calls the `editor` role, anchors each `original` in the message text (dropping and logging ones that are not found), keeps at most `EDITOR_MAX_SUGGESTIONS`, links `option_id`s, and queues unknown words in `review_queue`.
- [x] Models and migration for `editor_runs`, `suggestions`, `suggestion_options`, `events`, plus `events.py` with the event payload models and `record_event()`.
- [x] `evals/editor_gold.yaml`: thirty sentences you write yourself, each with fields like these:

  ```yaml
  - id: migration-hard
    text: Yeah the migration was really hard and we had a big problem with the old data, but we fixed it in the end.
    must_flag: [really hard, fixed]
    may_flag: [big problem]
    must_keep: [migration, data]
    acceptable_options:
      fixed: [resolved, patched, worked around, mitigated]
    forbidden_options: [utilised, leveraged, facilitated]
  ```

  Include about eight sentences where nothing should change, so the eval catches an editor that always suggests something.
- [x] `uv run vocab eval editor [--model <litellm-model>] [--prompt-version N]` reports: flag recall (share of `must_flag` spans flagged), false-flag rate (flags on `must_keep` words or on sentences that need no change), option acceptability (share of options in `acceptable_options`), inflation count (options from `forbidden_options`), schema failure rate, and median latency. It writes results to `evals/results/<date>-<model>-v<N>.json`.

#### Done when

- The eval runs against at least one local model and one hosted model, and you have chosen the editor model from the results.
- On your chosen model: flag recall of at least 0.8, false-flag rate of at most 0.1, zero inflation, and schema failures of at most 1 in 30. Adjust these thresholds once you see real numbers, but write the chosen thresholds into this file.

#### Prompt for Claude Code

```text
Read CLAUDE.md and "Editor contract", "One message through the system" and "Editor output"
in docs/DESIGN.md. Implement the "Editor and its eval" section of docs/PLAN.md. I will write
evals/editor_gold.yaml myself; create the file with three example entries and the schema
documented at the top, then build the eval command. Propose your plan first.
```

## Conversation UI

#### Goal

You can hold a conversation in the browser, see editor feedback under each of your messages, and accept or dismiss suggestions.

#### Tasks

- [x] Models and migration for `conversations`, `messages` and `message_lemma_counts`.
- [x] `prompts/partner.v1.md` implementing "Partner contract", with a placeholder for due words (empty until the "Practice loop" section).
- [x] Pages: conversation list, new conversation (choose a topic or scenario), conversation view.
- [x] Posting a message: store it, run the analyzer and store lemma counts, start the partner stream and the editor run concurrently.
- [x] Partner reply streamed over SSE with `sse-starlette` and the htmx SSE extension.
- [x] Editor feedback panel swapped in under the user's message when ready, with the original words highlighted using the stored offsets.
- [x] Accept and dismiss buttons that record events; accepting also marks the choice in the panel.
- [x] An editor failure shows "No feedback for this message" and never blocks the partner reply.
- [x] Every route uses `current_user` and `authorize()`.

#### Done when

- A ten-message conversation works end to end in the browser.
- `events` contains `suggestion_shown` for each displayed suggestion and one `suggestion_accepted` or `suggestion_dismissed` per click.
- Forcing the editor to fail (for example, a bad model name) leaves the conversation usable.

#### Prompt for Claude Code

```text
Read CLAUDE.md and "Partner contract", "Conversation" and "Why server-rendered pages
instead of a single-page app" in docs/DESIGN.md. Implement the "Conversation UI" section
of docs/PLAN.md. Keep templates plain and functional; styling comes later. Propose your
plan first, including how the partner stream and the editor run share the request.
```

## Practice loop

#### Goal

Accepted words come back: the partner steers towards due words, unprompted correct uses are detected and reviewed, and a small review page covers words that don't come up.

#### Tasks

- [x] Model and migration for `srs_cards`.
- [x] `practice/srs.py`: create a card on `suggestion_accepted`; review with `fsrs.Scheduler`; store `Card.to_dict()` and copy `due` into `due_at`; record `card_reviewed` events.
- [x] Due-word selection: up to three overdue options per user, most overdue first, passed into the partner prompt.
- [x] Prompted check as defined in "Practice and spaced repetition".
- [x] `prompts/usage_judge.v1.md` and the judge call, run only when `find_learned_words` returns hits.
- [x] `word_used` events, and FSRS reviews mapped as in the ratings table in the design.
- [x] `/review` page: shows a due option's distinction and a cloze sentence; the user types the word and rates the card.
- [x] `uv run vocab srs rebuild --user <id>` replays `card_reviewed` events into `srs_cards`, with a test that the rebuilt state matches.

#### Done when

- Accepting `resolve`, then writing a later message that uses "resolved" correctly with no prompt, produces a `word_used` event with `prompted=false`, `correct=true` and a `Good` review.
- Using a word that the partner used in the previous message produces `prompted=true` and no review.
- The partner prompt for a user with due cards contains those words, and the partner's replies do not contain them (checked in a `@pytest.mark.llm` test).

#### Prompt for Claude Code

```text
Read CLAUDE.md and "Practice and spaced repetition" and "Usage judge" in docs/DESIGN.md.
Implement the "Practice loop" section of docs/PLAN.md. Check the installed fsrs version's
Scheduler, Card and Rating API before using it. Propose your plan first.
```

## Rewrite drills

#### Goal

A drill page that gives you a vague sentence, takes your rewrite, and grades it.

#### Tasks

- [x] Models and migration for `drills` and `drill_attempts`.
- [x] `prompts/drill_gen.v1.md`: given a precision group, write one natural, vague sentence from a workplace or everyday context where one of the group's options is the best fit by a clear margin. Output the sentence and the intended option.
- [x] `prompts/drill_grade.v1.md`: rubric scores from 1 to 5 for precision, correctness of meaning and naturalness, plus one sentence of feedback and a better version if the score is below 4.
- [x] Drill selection: prefer groups with due cards, then groups the user's overuse lift points at, then random approved groups.
- [x] `/drills` page with a sentence, a text box, the grade, and a "next" button.
- [x] `drill_graded` events; a correct use of a carded option reviews that card with `Good`.

#### Done when

- Ten drills in a row work without errors, and the grades match your own judgement on at least eight.
- Drills prefer groups with due cards when such cards exist (unit test on the selector).

#### Prompt for Claude Code

```text
Read CLAUDE.md and "Purpose and scope" and "Practice and spaced repetition" in
docs/DESIGN.md. Implement the "Rewrite drills" section of docs/PLAN.md. Propose your plan
first, including the exact JSON schemas for the drill generator and grader outputs.
```

## Dashboard

#### Goal

A page showing whether your vocabulary is improving, built only from recorded data.

#### Tasks

- [x] `metrics/queries.py`: every metric in "Metrics", as functions taking `user_id` and a date range.
- [x] `metrics/lexical.py`: MTLD with a threshold of 0.72, forward and backward passes averaged, returning `None` below 100 words. Unit test against a hand-calculated example.
- [x] `/dashboard`: weekly crutch rate (line chart), top ten overused words by lift with suggested precision groups next to each, acceptance rate, spontaneous correct use, misuse rate, drill score trend, and MTLD.
- [x] A per-word view: for one crutch lemma, its weekly rate and the options learned from its groups with their usage counts.
- [x] A filter by `prompt_version` and model for acceptance rate, so editor changes can be told apart from user progress.

#### Done when

- With a seeded fixture of two weeks of messages and events, each metric function returns the value you calculated by hand (unit tests).
- The dashboard renders with real data from your own use.

#### Prompt for Claude Code

```text
Read CLAUDE.md and "Metrics" and "Events and LLM calls" in docs/DESIGN.md. Implement the
"Dashboard" section of docs/PLAN.md, test-first: build a fixture with known values and write
the metric tests before the queries. Propose your plan first.
```

## Product readiness (later)

These are for when other people start using the app. Each is independent.

- [x] Move to Postgres: add a Postgres service, point `DATABASE_URL` at it, run migrations, copy data with a script, and add Postgres row-level security on per-user tables as a second layer behind `authorize()`.
- [x] Account export (`/account/export` as JSON) and deletion (removes every row with the user's `user_id`, including `events`, and the `identities` rows).
- [x] Privacy notice that says which LLM providers receive users' messages.
- [x] Per-user rate limits and cost limits on LLM calls, using `llm_calls`.
- [x] Production deployment: HTTPS for the app and authentik, secure cookies, secrets outside `.env`.
- [x] Review the authentik enterprise licence and the wordfreq data terms before any commercial launch.

OpenFGA is out of scope for the personal phase. authentik covers login; `authorize()` stays an owner check until cross-user roles exist.

## What you see and what is causing it

| What you see | What is causing it |
|---|---|
| Claude Code builds features from later sections | The prompt did not limit it to one section; use the section's prompt, which says so |
| Tests pass but the app fails against real models | Only `FakeLLM` was exercised; run the `@pytest.mark.llm` tests with `RUN_LLM_TESTS=1` before closing a section |
| Editor quality is unclear after a prompt change | The eval was not rerun; run `vocab eval editor --prompt-version N` and compare result files |
| `vocab setup-nlp` fails behind a proxy | NLTK refuses proxied downloads unless `NLTK_ALLOW_PROXIED_URLOPEN=1` is set |
| A dependency changed without anyone deciding to change it | Installation used `uv sync` without `--locked`, or `uv lock --upgrade` was run without review |
| The dashboard shows nothing for spontaneous use | No cards are due yet, or the partner prompt is missing the due words; check `srs_cards.due_at` and the rendered partner prompt in `llm_calls` |
