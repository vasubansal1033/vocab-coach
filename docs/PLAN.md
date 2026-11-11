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

## Conversation improvements

#### Goal

Conversations feel like real writing tasks for a professional, and a suggestion can be used straight away instead of only days later.

#### Decisions already made

- Presets are a constant in the frontend. There is no presets table and no new API for them.
- "Retry with this word" is done on the server, because suggestion offsets are computed by the app and the server holds the original message. If the suggestion has no `suggestion_accepted` event yet, retry also calls the existing `accept_suggestion()`, so the card is created exactly once and the acceptance rate stays meaningful.
- The recap is computed on request and does not end the conversation. The user can keep writing after it.
- Flow mode is chosen when the conversation is created and cannot be changed later. In flow mode the frontend does not request per-message feedback, so the editor does not run and no `suggestion_shown` event is recorded during the conversation. The recap then runs the editor for every user message that has no editor run yet. This keeps the "prompted" rule correct: a suggestion the user never saw cannot make a later use count as prompted.

#### Files to change

- `src/vocab/conversation/models.py` and a migration: `flow_mode` and `allow_idioms` booleans on `conversations` (both default false). `allow_idioms` is stored now and used in the Idioms section.
- `src/vocab/events.py`: `SuggestionRetriedPayload` and its entry in `PAYLOAD_MODELS`.
- `src/vocab/conversation/service.py`: `retry_suggestion()` and `conversation_recap()`.
- `src/vocab/api/routes.py` and `src/vocab/api/schemas.py`:
  - `POST /api/conversations/{conversation_id}/suggestions/{suggestion_id}/retry` with body `{"option_id": "<suggestion option id>"}`, returning `{"text": "<rewritten message>"}`.
  - `GET /api/conversations/{conversation_id}/recap`.
  - Accept `flow_mode` and `allow_idioms` on conversation creation and return them on read.
- `frontend/src/pages/NewConversationPage.tsx`: preset buttons and a flow mode checkbox. `frontend/src/components/MessageFeedback.tsx`: the retry button. `frontend/src/pages/ConversationPage.tsx`: put the retry text in the message box, add a "Finish and show recap" button and the recap view, and skip feedback requests in flow mode. `frontend/src/api.ts`: the new calls.
- `docs/DESIGN.md`: move the new columns and event from "Planned tables, events and roles" into "Data model".

#### Tasks

- [x] Writing-task presets on the new conversation page. Each preset fills `title` and `feedback_expectations` and sets `allow_idioms`:

  | Preset | Register in `feedback_expectations` | `allow_idioms` |
  |---|---|---|
  | Reply to a client email | Formal and polite, clear commitments | false |
  | Team chat update | Neutral and brief | true |
  | Standup summary | Neutral, past and next steps | true |
  | Giving difficult feedback | Neutral, specific and kind | false |
  | Declining a request | Polite and firm | false |
  | Meeting summary | Neutral, decisions and owners | false |

- [x] Retry with this word: the server replaces `messages.content[span_start:span_end]` with the option's word, records `suggestion_retried`, accepts the suggestion if it was not accepted, and returns the text. The frontend puts the text in the message box; the user edits and sends it as a normal message.
- [x] Recap, built from recorded data with no new LLM role:
  - Words to keep: options accepted in this conversation, then the highest-ranked shown and not dismissed suggestion options, up to three in total.
  - Crutch words: lemmas from `message_lemma_counts` for this conversation's user messages where `is_crutch()` is true, with counts, most frequent first.
  - One sentence to rewrite: the sentence of a user message that holds the highest-ranked suggestion that was neither accepted nor dismissed. Find the sentence boundaries with the existing spaCy analyzer, not with a regex.
- [x] Flow mode as described in "Decisions already made".

#### Done when

- Retrying with an option and then sending the message produces a `word_used` event with `prompted=true` (the word was just suggested) and no FSRS review, and exactly one `suggestion_accepted` event exists for that suggestion even if the user also clicked accept.
- A unit test with a seeded conversation checks every part of the recap.
- In a flow-mode conversation, no `editor_runs` rows and no `suggestion_shown` events exist before the recap is requested, and after it every user message has an editor run.
- `uv run pytest` and `uv run ruff check .` pass, and `npm run build` in `frontend/` succeeds.

#### Prompt for the coding agent

```text
Read CLAUDE.md, docs/HANDOVER.md, and "Purpose and scope", "Partner contract",
"Practice and spaced repetition" and "Planned tables, events and roles" in docs/DESIGN.md.
Implement the "Conversation improvements" section of docs/PLAN.md. Its "Decisions already
made" are fixed; ask before changing any of them. Propose your plan first.
```

## Drill improvements

#### Goal

Drills have one clearly best answer, give help before the user gives up, and come in sets of five with a summary.

#### Decisions already made

- Context comes from a new prompt version, `prompts/drill_gen.v2.md`. `v1` is never edited. The default `llm_drill_gen_prompt_version` in `config.py` and `.env.example` becomes 2.
- Hints need no LLM call. Level 1 is the intended option's `distinction`, level 2 is the first letter of `intended_word`, level 3 is the list of the group's approved option words. Using hints does not change the score; the grade only shows how many were used.
- Disputes are only recorded as events. A web request never writes files. A CLI command exports disputes to a file for review.
- Sets of five are counted in the frontend. The summary comes from the server, so it uses stored scores and not values held in the browser.

#### Files to change

- `src/vocab/drills/schemas.py`: `DrillGenOutputV2` with `context: str` in addition to the v1 fields. `src/vocab/drills/service.py` picks the output model by the active prompt version.
- `src/vocab/drills/models.py` and a migration: `drills.context` (nullable text), `drill_attempts.hints_used` (integer, default 0).
- `src/vocab/events.py`: `DrillDisputedPayload`.
- `src/vocab/drills/service.py`: `hint_for()`, `summarize_attempts()` (a pure function over `DrillAttempt` rows), `dispute_attempt()`.
- `src/vocab/api/routes.py` and `src/vocab/api/schemas.py`:
  - `GET /api/drills/{drill_id}/hint?level=1|2|3`.
  - `hints_used` in the attempt request body.
  - `POST /api/drills/attempts/{attempt_id}/dispute` with body `{"note": str | null}`.
  - `GET /api/drills/summary?attempt_ids=a,b,c`, filtered by `user_id`.
- `src/vocab/cli.py`: `uv run vocab eval drill-disputes` writes `evals/drill_disputes/<YYYY-MM-DD>.yaml` with the drill, context, answer, grade and note for each dispute since the last export date found in that folder.
- `frontend/src/pages/DrillsPage.tsx` and `frontend/src/api.ts`.

#### Tasks

- [x] `prompts/drill_gen.v2.md`: one or two sentences of context, then the vague sentence, written so the intended option is the best fit by a clear margin.
- [x] Hints as decided above; the hints used are stored on the attempt and shown in the grade.
- [x] The grade view shows the user's rewrite next to `better_version` when there is one. Otherwise it shows the rewrite next to the intended word with its distinction. The grader's feedback sentence goes under both.
- [x] Dispute button, `drill_disputed` event, and the export CLI.
- [x] Sets of five, then a summary: mean score, the words practised, and the total hints used.

#### Done when

- Ten drills from `v2` each have one clearly best option in your own judgement (run with a real model and `RUN_LLM_TESTS=1`).
- Unit tests cover `hint_for()` at all three levels, `summarize_attempts()` with known scores, and the dispute export output.
- `v1` drills already in the database still render (their `context` is null).
- `uv run pytest`, `uv run ruff check .` and `npm run build` pass.

#### Prompt for the coding agent

```text
Read CLAUDE.md, docs/HANDOVER.md, and the "Rewrite drills" and "Drill improvements"
sections of docs/PLAN.md. Implement "Drill improvements". Its "Decisions already made"
are fixed; ask before changing any of them. Propose your plan first.
```

## Choose the word

#### Goal

A fast recognition exercise built on the existing precision groups. This section also creates the shared `exercises` tables that Compare and Idioms reuse.

#### Decisions already made

- Items are stored in the shared `exercises` and `exercise_attempts` tables (see "Planned tables, events and roles" in the design) with `item_type="choice"`. The code lives in a new module `src/vocab/exercises/`, and Compare and Idioms add their item types to it.
- `choice_gen` is a new LLM role. Its output must use only option IDs from the group it was given. The service rejects the output (and records the failed call as usual) if any ID is unknown, if not exactly one candidate is marked best, or if the sentence does not contain exactly one `___`.
- An answer is correct when the best pick matches. Which other candidates the user marked is shown as feedback and stored, but does not change `correct`.
- Group selection reuses `drills/select.py` `select_group()`, restricted to `kind="precision"` once that column exists.
- A correct best pick for a carded option reviews the card with `Good` and source `exercise`.

#### Files to change

- New `src/vocab/exercises/` with `models.py` (`Exercise`, `ExerciseAttempt`), `schemas.py` (`ChoiceGenOutput`, `ChoicePrompt`, `ChoiceAnswer`, `ChoiceResponse`), `service.py` (`create_choice()`, `answer_exercise()`), and `grading.py` (`grade_choice()`, a pure function).
- A migration for both tables.
- `src/vocab/llm/roles.py` (`Role`, `ROLES`, `model_for`, `prompt_version_for`), `src/vocab/config.py`, `.env.example`: the `choice_gen` role.
- `src/vocab/prompts/choice_gen.v1.md`.
- `src/vocab/events.py`: `ExerciseAnsweredPayload`, and `"exercise"` added to the `source` literal of `CardReviewedPayload`. `src/vocab/practice/srs.py`: `"exercise"` added to `Source`.
- `src/vocab/account/service.py`: export and delete both new tables. `infra/postgres/rls.sql`: enable RLS on both tables.
- `src/vocab/api/routes.py` and `src/vocab/api/schemas.py`: `POST /api/exercises/choice` (create), `GET /api/exercises/{exercise_id}` (returns `prompt` only), `POST /api/exercises/{exercise_id}/attempt`.
- `frontend/src/pages/DrillsPage.tsx`: tabs "Rewrite" and "Choose the word". `frontend/src/api.ts`.

#### Tasks

- [ ] `choice_gen` role, prompt and output schema: a `situation` (one sentence), a `sentence` with one `___`, and four to six `candidates`, each with `option_id`, `fit` (`fits`, `partly`, `wrong`), `reason` (one line) and `best` (boolean).
- [ ] Tables, migration, account export and delete, RLS.
- [ ] `grade_choice()` and the attempt endpoint; record `exercise_answered`; review the card on a correct best pick.
- [ ] "Choose the word" tab.

#### Done when

- Twenty generated items each have exactly one best answer, and you agree with the `fit` labels on at least eighteen.
- `grade_choice()` has unit tests for a correct best pick, a wrong best pick, and a correct best pick with a wrongly marked extra candidate.
- `GET /api/exercises/{id}` never includes `answer` (API test).
- Account export includes exercises and account deletion removes them (extend the existing account tests).
- `uv run pytest`, `uv run ruff check .` and `npm run build` pass.

#### Prompt for the coding agent

```text
Read CLAUDE.md, docs/HANDOVER.md, and "Choose the word", "Planned tables, events and
roles" and "Practice and spaced repetition" in docs/DESIGN.md. Implement the "Choose the
word" section of docs/PLAN.md. Its "Decisions already made" are fixed; ask before changing
any of them. Propose your plan first, including the exact JSON schema for choice_gen.
```

## Word sets

#### Goal

The lexicon can hold confusable sets and idioms as well as precision groups, without changing how cards, usage detection or metrics work.

#### Decisions already made

- Extend `precision_groups` and `precision_options`; do not rename them or add parallel tables. See "Word sets: one lexicon for all modes" in the design for the columns and the `details` fields.
- Seed files stay in `data/precision_groups/`. A missing `kind` means `precision`. Group ID conventions: `confusable.<word>-<word>` (for example `confusable.imply-infer`) and `idiom.<head_lemma>` (for example `idiom.agree`). Option IDs keep using `lexicon/service.py` `option_id()`.
- Multi-word matching already works: `nlp/usage.py` `find_learned_words()` uses a spaCy `PhraseMatcher` on `LEMMA`. Add tests; change the code only if a test fails.
- Drafting uses two new roles, `confusable_gen` and `idiom_gen`, instead of a new `group_gen` version, so existing precision drafting does not change.

#### Files to change

- `src/vocab/lexicon/models.py` and a migration (`render_as_batch` is already on, which SQLite needs to make `head_lemma` nullable).
- `src/vocab/lexicon/schemas.py`: `ConfusableDetails`, `IdiomDetails`, and validation of `details` by kind for seeds and drafts.
- `src/vocab/lexicon/service.py`:
  - `load_seeds()` reads `kind` and `details`.
  - `export_approved()` writes them back.
  - `approved_groups_for_lemma()` gains a `kinds` parameter that defaults to `("precision",)`.
  - New `draft_set()` for the two new kinds.
- `src/vocab/drills/select.py` `_approved_groups()`: filter `kind="precision"`. Check every other query on `PrecisionGroup` in `src/vocab/` (`grep -rn PrecisionGroup src/vocab`) and decide per query whether it needs the filter. `metrics/queries.py` `_groups_for_head()` does.
- `src/vocab/lexicon/admin.py` and its template: show `kind` and `details`.
- `src/vocab/llm/roles.py`, `src/vocab/config.py`, `.env.example`: `confusable_gen` and `idiom_gen`. Prompts `confusable_gen.v1.md` and `idiom_gen.v1.md`.
- `src/vocab/cli.py`: `uv run vocab lexicon draft --kind confusable --words imply,infer` and `uv run vocab lexicon draft --kind idiom --lemma agree`. Without `--kind`, the command behaves as today.
- `docs/DESIGN.md`: move the lexicon changes into "Data model" and "Precision groups".

#### Tasks

- [ ] Migration and models.
- [ ] `details` Pydantic models and loader validation.
- [ ] `kind` filters on editor, drill and metric queries.
- [ ] Matching tests: "We were cutting corners on testing" matches `cut corners`, and "They saw eye to eye on scope" matches `see eye to eye`.
- [ ] One seed file per new kind, used by tests: `confusable.imply-infer.yaml` and `idiom.agree.yaml` (two idioms such as "on the same page" and "see eye to eye").
- [ ] Two new drafting roles and the CLI options.

#### Done when

- All existing tests pass with no changes to `practice/srs.py`, `practice/usage.py` or the metric functions, apart from the `kind` filter.
- `uv run vocab lexicon load` loads both new seed files, and the admin page shows them.
- The editor's input for a message containing "agree" contains no idiom groups (the editor only gets idioms after the Idioms section).
- `uv run pytest` and `uv run ruff check .` pass.

#### Prompt for the coding agent

```text
Read CLAUDE.md, docs/HANDOVER.md, and "Data model", "Precision groups" and "Word sets: one
lexicon for all modes" in docs/DESIGN.md. Implement the "Word sets" section of
docs/PLAN.md. Its "Decisions already made" are fixed; ask before changing any of them.
Propose your migration and plan first.
```

## Compare

#### Goal

The user can see how near-synonyms differ and practise telling them apart.

#### Decisions already made

- Practice items use the shared `exercises` tables with item types `compare_pair`, `compare_misuse` and `compare_order`.
- `compare_gen` is a new role that writes `compare_pair` and `compare_misuse` items. `compare_order` items need no LLM: the order comes from `details.strength`, and they are only offered for sets where every option has a `strength`.
- Compare cards are built from stored lexicon fields only. No LLM call runs when a card is opened.

#### Files to change

- `data/precision_groups/`: at least ten reviewed confusable sets drafted with `confusable_gen`: imply and infer, persuade and convince, continual and continuous, sceptical and cynical, affect and impact, assure and ensure, comprise and compose, fewer and less, principal and principle, and annoyed, irritated, exasperated and livid (with `strength`).
- `src/vocab/exercises/`: compare schemas, `create_compare()`, and grading functions per item type.
- `src/vocab/llm/roles.py`, `src/vocab/config.py`, `.env.example`, `src/vocab/prompts/compare_gen.v1.md`.
- `src/vocab/api/routes.py` and `src/vocab/api/schemas.py`:
  - `GET /api/compare` (list sets).
  - `GET /api/compare/{group_id}` (card).
  - `POST /api/exercises/compare` with body `{"group_id": ..., "item_type": ...}`.
- New `frontend/src/pages/ComparePage.tsx` (list and card) at `/compare` and `/compare/:groupId`, and a nav link in `frontend/src/App.tsx`.

#### Tasks

- [ ] Seed and review the ten confusable sets.
- [ ] Compare card page.
- [ ] `compare_gen` role and the three item types with grading functions.
- [ ] `exercise_answered` events and card reviews, as in Choose the word.

#### Done when

- Every seeded set renders as a card with all fields filled.
- Ten generated items of each LLM-written type have one correct answer in your own judgement on at least eight.
- The grading functions for all three types have unit tests.
- `uv run pytest`, `uv run ruff check .` and `npm run build` pass.

#### Prompt for the coding agent

```text
Read CLAUDE.md, docs/HANDOVER.md, and "Compare", "Word sets: one lexicon for all modes"
and "Planned tables, events and roles" in docs/DESIGN.md. Implement the "Compare" section
of docs/PLAN.md. Its "Decisions already made" are fixed; ask before changing any of them.
Propose your plan first.
```

## Idioms

#### Goal

The user learns everyday idioms for workplace writing in steps, from recognition to unprompted use, without being pushed to overuse them.

#### Decisions already made

- The everyday tier comes first. The literary tier is the last task in this section and can be split into its own session.
- Steps 1 to 3 (recognise, meaning, situation) are `exercises` items of types `idiom_recognise`, `idiom_meaning` and `idiom_situation`, written by a new version `compare_gen.v2.md` that adds these types. `compare_gen.v1.md` is not edited.
- Step 4 (write your own sentence) calls the existing `usage_judge` with the idiom's `details.meaning` as the distinction. No new grading role.
- Step 5 is the existing unprompted-use detection, with no new code.
- The editor gets idiom groups only when `conversations.allow_idioms` is true and no `suggestion_shown` event in that conversation points to an idiom group. This filter is done in Python before the editor call, not left to the prompt.
- Idiom suggestions need a new editor prompt version (`editor.v4.md`), because v3 does not describe idiom groups. The default `llm_editor_prompt_version` changes to 4 only after the eval shows no regression.

#### Files to change

- `data/precision_groups/`: about thirty reviewed everyday idioms in `idiom.<head_lemma>` groups, drafted with `idiom_gen`. None of them has a pronoun slot.
- `src/vocab/exercises/`: idiom item schemas and grading.
- `src/vocab/prompts/compare_gen.v2.md` and `src/vocab/prompts/editor.v4.md`.
- `src/vocab/editor/service.py` `analyze_message()`: add idiom groups under the rule above.
- `evals/editor_gold.yaml`: at least five idiom cases (two where an idiom fits, three where it must not be suggested).
- `src/vocab/metrics/queries.py`: `idiom_misuse_rate()`; `misuse_rate()` excludes idiom options. `src/vocab/api/routes.py` dashboard output and `frontend/src/pages/DashboardPage.tsx`.
- New `frontend/src/pages/IdiomsPage.tsx` at `/idioms`, showing `avoid_when` on every idiom card, and a nav link.

#### Tasks

- [ ] Seed and review thirty everyday idioms.
- [ ] Idiom page with steps 1 to 4.
- [ ] Editor idiom filter, `editor.v4.md`, gold cases, and an eval run with v3 and v4 compared.
- [ ] Separate idiom misuse rate on the dashboard.
- [ ] Literary tier: about twenty idioms with `origin`, shown on the idiom card.

#### Done when

- An idiom accepted from a suggestion and later used unprompted and correctly produces a `word_used` event with `prompted=false` and a `Good` review.
- `uv run vocab eval editor --prompt-version 4` scores no lower than `--prompt-version 3` on the existing (non-idiom) gold cases. Both result files are committed under `evals/results/`.
- A unit test shows that the editor input contains no idiom groups when `allow_idioms` is false, or after one idiom suggestion was shown in that conversation.
- `uv run pytest`, `uv run ruff check .` and `npm run build` pass.

#### Prompt for the coding agent

```text
Read CLAUDE.md, docs/HANDOVER.md, and "Idioms", "Editor contract", "Metrics" and "Planned
tables, events and roles" in docs/DESIGN.md. Implement the "Idioms" section of
docs/PLAN.md, everyday tier first. Its "Decisions already made" are fixed; ask before
changing any of them. Propose your plan first.
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
