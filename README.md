## vocab-coach

vocab-coach is a writing coach that helps you replace vague, general English words ("good", "fix", "big problem", "really hard") with precise ones. It is built for non-native English speakers who work in English and want richer, more exact vocabulary in emails, chat messages, status updates and reviews. It is a writing tool only: there is no voice input or pronunciation practice.

You write to an AI conversation partner, and after each message an editor model points out where a more precise word would say something truer. Words you accept become spaced-repetition cards, and later conversations steer you toward situations where those words fit, so you practise them in your own sentences. A dashboard then shows whether the new words are appearing in your writing without prompting.

The app started as a personal tool. It already has per-user data, login through an OpenID Connect provider, and per-user rate limits, so it can grow into a multi-user product without rewriting the data layer.

#### What you can do

**Conversations with word-choice feedback.** Start a conversation from a writing-task preset (client email, team chat update, standup summary, difficult feedback, declining a request, meeting summary) or from your own scenario. After each message the editor suggests at most a few more precise words and explains how each option changes the meaning. Feedback appears under each message, and the recap at the end lists words worth keeping, your crutch words, and one sentence to rewrite.

![A conversation with wording feedback and the end-of-conversation recap](docs/screenshots/conversation-feedback.png)

"Retry with this word" puts your message back in the message box with the suggested word swapped in, so you can send the improved version straight away. It also counts the suggestion as accepted, which creates the review card at once instead of days later.

![The message box filled with the rewritten message after choosing Retry with this word](docs/screenshots/retry-with-word.png)

Flow mode, chosen when you create the conversation, lets you write without interruption. The editor does not run until you ask for the recap, and then it reviews every message you wrote. Waiting is deliberate: a suggestion you never saw must not make a later use of that word look "prompted" in the metrics.

![The recap of a flow-mode conversation, where feedback was held back until the end](docs/screenshots/flow-mode-recap.png)

![Starting a new conversation from a writing-task preset](docs/screenshots/new-conversation.png)

**Rewrite drills.** The app writes a short context and a deliberately vague sentence aimed at one word group. You rewrite it, optionally using up to three hints, and a grader scores precision, meaning and naturalness from 1 to 5. Hints come in steps: first what the better word adds, then its first letter, then the list of options. Hints do not change the score, but the grade and the summary show how many you used.

![A rewrite drill with two hints used](docs/screenshots/drill-hints.png)

After grading you see your rewrite next to the intended word, and you can dispute a grade you disagree with. Disputes are recorded as events so they can be exported for reviewing the grader.

![A graded rewrite drill](docs/screenshots/rewrite-drill.png)

Drills come in sets of five, and the set ends with a summary built from the stored scores.

![The summary at the end of a set of five drills](docs/screenshots/drill-set-summary.png)

**Choose the word.** A situation and a sentence with one blank. You mark every candidate that fits and pick the best one. Feedback explains each candidate in one line.

![Feedback on a choose-the-word exercise](docs/screenshots/choose-the-word.png)

**Compare.** Near-synonyms side by side, such as persuade and convince, with the core difference, connotation, register, typical word pairings and an example for each. Practice items ask you to fill sentences with the right word, spot a misused word, or order words by strength.

![A comparison card for persuade and convince](docs/screenshots/compare-card.png)

Sets whose words form a natural scale, such as annoyed, irritated, exasperated and livid, also offer the ordering exercise.

![Ordering annoyed, irritated, exasperated and livid by strength](docs/screenshots/compare-order.png)

**Idioms.** Everyday workplace idioms and literary allusions, each with its meaning, an example, a common misuse and when to avoid it. You learn each idiom in steps: recognise it, pick its meaning, pick the situation it fits, then write your own sentence. The sentence is checked by the same usage judge that checks words in conversations. The editor suggests an idiom only in conversations where you turned idioms on, and at most one per conversation.

![An idiom card with usage notes and practice steps](docs/screenshots/idiom-card.png)

![Writing a sentence with an idiom and getting it judged](docs/screenshots/idiom-write.png)

**Review.** Spaced-repetition cards, scheduled with FSRS, for the words you accepted. Words you use correctly in a conversation or drill are reviewed automatically, so the review page only needs to cover words that did not come up.

![The review page](docs/screenshots/review.png)

**Dashboard.** Your weekly crutch-word rate, the words you overuse compared with general English, how often you accept suggestions, how often learned words appear unprompted, how often they are misused, drill scores over time, and lexical diversity (MTLD). Every number is computed from recorded events, not from counters updated in place.

![The dashboard](docs/screenshots/dashboard.png)

**Works on a phone.** The layout adapts to narrow screens, so you can do a drill or review a card on the move.

<p>
  <img src="docs/screenshots/mobile-conversation.png" alt="A conversation with feedback on a phone-sized screen" width="260">
  <img src="docs/screenshots/mobile-dashboard.png" alt="The dashboard on a phone-sized screen" width="260">
</p>

The screenshots show sample data for a fictional learner, taken in a headless browser at desktop and phone widths. The model replies in them were canned for the demo and were not generated live, so they illustrate the interface and not the quality of any particular model.

#### How it works

1. You send a message. The language analyzer (spaCy) finds candidate vague words, and the lexicon supplies approved precision groups for them: one vague word in one sense, with precise options and what each option adds.
2. The editor role returns validated suggestions. The app locates each suggested span in your message itself, because model-reported character offsets are not trusted.
3. A suggestion you accept creates an FSRS card. When you later use that word, a usage judge checks whether you used it correctly, and the app records whether you were prompted (the partner or a suggestion had just shown the word) or used it unprompted.
4. Only unprompted correct uses count towards the "spontaneous use" metric on the dashboard.

The design reasoning is in `docs/DESIGN.md`.

#### Tech stack

- Backend: Python 3.13+, FastAPI, SQLAlchemy and Alembic, SQLite for development with a Postgres path (including row-level security) for production.
- Frontend: a React and TypeScript single-page app built with Vite, served by FastAPI from `frontend/dist`.
- Language tools: spaCy, NLTK WordNet and wordfreq.
- LLMs: LiteLLM for provider access and LangGraph for role workflows. Only `src/vocab/llm/` imports either of them. Each job (partner, editor, grader and so on) is a named role, and each role gets its model from settings, so you can mix providers, including a local Ollama model.
- Spaced repetition: FSRS.
- Login: authentik through OpenID Connect, started with Docker Compose.
- Tooling: uv, pytest and ruff.

#### Getting started

You need Python 3.13 or newer, [uv](https://docs.astral.sh/uv/), Node.js with npm, and Docker (for the login provider). These steps were checked against this repository on 11 Nov 2026.

1. Install the Python dependencies exactly as pinned in `uv.lock`, and download the language data:

   ```bash
   uv sync --locked
   uv run vocab setup-nlp
   ```

2. Build the frontend. FastAPI serves the built files, so the app shows no UI until this is done:

   ```bash
   cd frontend && npm install && npm run build && cd ..
   ```

3. Create your settings file and fill it in:

   ```bash
   cp .env.example .env
   ```

   Replace the `replace-me` placeholder for `SESSION_SECRET` with a random value (for example from `openssl rand -hex 32`). The app starts with the placeholder, but anyone who knows it could forge a session cookie. Set one model per LLM role as described in "Configuring the language models" below.

4. Start the login provider and connect the app to it. `infra/authentik/README.md` explains this in full. In short, start it with `docker compose -f infra/authentik/compose.yml up -d`, put the same `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` in both `infra/authentik/.env` and the root `.env`, and sign up your own user from the login page.

5. Create the database tables and run the app:

   ```bash
   uv run alembic upgrade head
   uv run uvicorn vocab.main:app --reload
   ```

   Open <http://localhost:8000>. You are sent to authentik to sign in.

6. Load the built-in word lists. The lexicon has no command-line importer; it is loaded through an admin-only API route. After your first sign-in, open <http://localhost:8000/api/me> to read your user id, set `ADMIN_USER_ID` to it in `.env`, and restart the app. Then, with your browser's `vocab_session` cookie value, call:

   ```bash
   curl -X POST -b "vocab_session=<cookie value>" http://localhost:8000/api/lexicon/import/builtin
   ```

   Until this step is done, the editor, drills and exercises have no words to work with.

#### Configuring the language models

Each role has its own model setting, so you can use a stronger model for the editor and grader and a cheaper one for the partner. Model strings use the form `provider/model`. Provider API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) are read from the environment by LiteLLM.

| Role | Setting | Job |
|---|---|---|
| `partner` | `LLM_PARTNER_MODEL` | Holds the conversation |
| `editor` | `LLM_EDITOR_MODEL` | Suggests more precise words |
| `usage_judge` | `LLM_USAGE_JUDGE_MODEL` | Checks whether a learned word was used correctly |
| `drill_gen` | `LLM_DRILL_GEN_MODEL` | Writes rewrite drills |
| `drill_grade` | `LLM_DRILL_GRADE_MODEL` | Grades rewrites |
| `choice_gen` | `LLM_CHOICE_GEN_MODEL` | Writes choose-the-word items |
| `compare_gen` | `LLM_COMPARE_GEN_MODEL` | Writes compare and idiom exercises |
| `group_gen` | `LLM_GROUP_GEN_MODEL` | Drafts precision groups |
| `confusable_gen` | `LLM_CONFUSABLE_GEN_MODEL` | Drafts sets of confusable words |
| `idiom_gen` | `LLM_IDIOM_GEN_MODEL` | Drafts idiom entries |

`.env.example` has ready-made blocks for OpenAI, Anthropic, Gemini and local Ollama models. Check a role with `uv run vocab llm ping editor`. Prompts are versioned files in `src/vocab/prompts/`, and a prompt file that has produced recorded data is never edited: the next version is a new file, chosen with the matching `LLM_*_PROMPT_VERSION` setting. Per-user daily call and cost limits are set with `LLM_RATE_LIMIT_PER_DAY` and `LLM_COST_LIMIT_USD_PER_DAY`.

#### Commands

```bash
uv run pytest                           # unit tests, no real LLM calls
RUN_LLM_TESTS=1 uv run pytest -m llm    # tests that call the configured models
uv run ruff check . && uv run ruff format --check .
uv run alembic revision --autogenerate -m "<message>"
uv run alembic upgrade head
uv run vocab eval editor                # editor quality eval against evals/editor_gold.yaml
uv run vocab eval drill-disputes        # export disputed drill grades for reviewing the grader
uv run vocab srs rebuild --user <id>    # rebuild card state by replaying review events
```

Unit tests use a fake LLM (`FakeLLM`), so they need no API keys. Tests that call real models are marked `llm` and run only when `RUN_LLM_TESTS=1`.

#### Project layout

```text
src/vocab/
  auth/          OIDC login, identities, current_user, authorize()
  llm/           litellm and LangGraph live only here: roles, graphs, limits, client
  prompts/       versioned prompt files, never edited after use
  nlp/           spaCy analyzer, candidate spans, learned-word matching
  lexicon/       precision groups, confusable sets, idioms, import and drafting
  editor/        message to suggestions
  conversation/  conversations, messages, feedback, recap
  practice/      FSRS cards, due words, usage detection
  drills/        rewrite drills: generation, hints, grading
  exercises/     choose-the-word, compare and idiom exercises
  metrics/       dashboard queries and MTLD
  api/           JSON API used by the React app
frontend/        React and TypeScript single-page app
evals/           editor gold set and eval results
infra/           authentik and Postgres setup
migrations/      Alembic migrations
tests/
```

#### Documentation

- `docs/DESIGN.md`: the design and the reasoning behind it.
- `docs/PLAN.md`: build order and progress, section by section.
- `docs/HANDOVER.md`: product decisions and checklists for contributors, including coding agents.
- `docs/PRODUCTION.md`: what to do before exposing the app beyond your own machine (HTTPS, secure cookies, Postgres, limits).
- `CLAUDE.md`: the working rules for the codebase, such as every user table carrying an indexed `user_id`, and no setting that skips authentication.

#### Data sources and licences

The lexicon can import public word data (Lexkite's confused-words list under CC BY 4.0 and the ABC Thesaurus under CC BY-SA 4.0), and the app uses spaCy, NLTK WordNet and wordfreq, each with its own licence and attribution terms. The app's own `/about/attribution` page lists them. Read those terms, and the authentik licence terms, before any commercial launch. This repository does not yet include a licence file for its own code, so choose one before you make the repository public.

#### What you see and what is causing it

| What you see | What is causing it |
|---|---|
| The app opens a plain page with no UI | The frontend was not built; run `npm run build` in `frontend/` |
| `RuntimeError: SESSION_SECRET is empty` on startup | `SESSION_SECRET` is blank or missing in `.env` |
| `ValueError: LLM_<ROLE>_MODEL is not configured` | The role's model is empty or still the placeholder `<local-model-tag>` in `.env` |
| Signing in fails with a redirect URI error | The redirect URI in authentik differs from `http://localhost:8000/auth/callback`; see `infra/authentik/README.md` |
| The editor never suggests anything, and drills fail | The lexicon is empty; do step 6 of "Getting started" |
| The lexicon import returns 404 | `ADMIN_USER_ID` is empty or does not match your user id |
| Requests fail with HTTP 429 after heavy use | The per-user daily call or cost limit was reached; see `LLM_RATE_LIMIT_PER_DAY` and `LLM_COST_LIMIT_USD_PER_DAY` |
