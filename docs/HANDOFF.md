# Handoff: vocab-coach

Written on 10 Nov 2026 for whoever continues this in Cursor. It says what is built, how to run it, what surprised us, and what to do next. Read `CLAUDE.md` first: its rules still apply, and Cursor does not load that file automatically, so open it or copy it into `.cursor/rules`.

## What the project is

vocab-coach is a FastAPI web app that helps a person replace vague English words with precise ones. The design is in `docs/DESIGN.md` and the build order is in `docs/PLAN.md`. The working rules are in `CLAUDE.md`. The most important rule is process: work on one `PLAN.md` section at a time, read the design sections it names, propose a plan, and wait for approval before writing code. Do not build features from later sections.

## Where things stand

| Section | State |
|---|---|
| Foundation | Done and verified |
| Login and users | Done and verified against a live authentik |
| Language analysis | Not started. A plan was requested but not yet written or approved |
| LLM client, Lexicon, Editor, Conversation UI, Practice loop, Drills, Dashboard | Not started |

The `PLAN.md` checkboxes for Foundation and Login and users are ticked. The project is not a git repository, so nothing is committed. Run `git init` before doing anything else if you want history.

Checks at the time of writing: `uv run pytest` passes (19 tests), `uv run ruff check .` and `uv run ruff format --check .` are clean, and `uv run alembic upgrade head` works on an empty database.

## How to run it

```bash
uv sync --locked
docker compose -f infra/authentik/compose.yml up -d
uv run alembic upgrade head
uv run uvicorn vocab.main:app --reload
```

The app is on `http://localhost:8000` and authentik is on `http://localhost:9000`. The home page requires login. Both a uvicorn process on port 8000 and the three authentik containers may still be running from the previous session, so check before starting new ones.

The root `.env` is git-ignored and already holds a generated `SESSION_SECRET`, the issuer, and the client ID and secret. `.env.example` lists every variable. The LLM model names in it are placeholders, because the LLM client section has not been built.

## What exists

- `src/vocab/config.py`: `Settings` with every variable from the design's "Configuration" table. `get_settings()` is cached.
- `src/vocab/db.py`: `Base`, `make_engine()` (installs the SQLite `foreign_keys=ON` and `journal_mode=WAL` pragmas on that engine only), and the `get_session` dependency.
- `src/vocab/main.py`: `create_app(settings=None)`. It refuses to start with an empty `SESSION_SECRET`. `/healthz` and `/static` are public, `/` requires login.
- `src/vocab/auth/`: `models.py` (`users`, `identities`), `service.py` (`get_or_create_user`), `oidc.py` (login, callback, logout), `deps.py` (`current_user`), `authorize.py`.
- `src/vocab/cli.py`: an `argparse` entry point named `vocab` with no subcommands yet. Later sections add them here.
- `src/vocab/web/`: Jinja templates and vendored htmx 2.0.11, htmx-ext-sse 2.2.4 and Chart.js 4.6.1, each with its licence file.
- `migrations/`: one revision, `9b7a26b4d622`, for `users` and `identities`. `env.py` imports `vocab.auth.models` so autogenerate sees the tables. Any new model module must be imported there too.
- `infra/authentik/`: the official Compose file, a `blueprints/vocab-coach.yaml`, and a README.
- `tests/`: `conftest.py` provides an in-memory SQLite engine, a `session`, an `app` wired to it, an anonymous `client`, `make_user`, and `login_as`.

## Things that were not obvious

These each cost time. Read them before changing the related code.

**authentik is configured by a blueprint, not by clicking in the admin UI.** `infra/authentik/blueprints/vocab-coach.yaml` is mounted into the worker and re-applied whenever the file changes. It creates the provider, the application with slug `vocab-coach`, and the sign-up flow. If the application ever goes missing, look for `Entry invalid` or `Blueprint validation failed` in the worker log. The client ID and secret come from `infra/authentik/.env`, and the same values must be in the root `.env`.

**Three settings in that blueprint are required, and each failure looked unrelated to its cause.**

- `grant_types: [authorization_code]` is empty by default in this authentik version. Without it, the authorize request is rejected with "invalid_request: The request is otherwise malformed", and the authentik log says "Invalid grant_type for provider".
- `invalidation_flow` must be `default-invalidation-flow`. The `default-provider-invalidation-flow` only shows "you have logged out of vocab-coach" and leaves the authentik session alive, so the next visit logs in again without asking for credentials.
- The entry that points the login page at the enrollment flow must repeat `user_fields: [email, username]`. Without them the serializer rejects the entry and the whole blueprint fails validation, so no application is created.

**The session holds only `user_id`.** That is a project rule, so there is no `id_token_hint` at logout. authentik accepts the logout request without it.

**Passwords and sign-up are done by a person.** The existing user row ("authentik Default Admin") came from logging in as `akadmin`. authentik's own sign-up flow was never completed by anyone, so it is untested beyond the link appearing on the login page.

**Tests need `SESSION_SECRET`.** `vocab.main` builds `app` at import time and refuses an empty secret, so `tests/conftest.py` sets it in `os.environ` before importing anything from `vocab`. Keep that import order.

**Ruff needs a bugbear setting for FastAPI.** `pyproject.toml` has `extend-immutable-calls = ["fastapi.Depends"]` so `Depends(...)` in argument defaults is not flagged.

**The package is named `vocab`, not `vocab_coach`.** `pyproject.toml` sets `[tool.uv.build-backend] module-name = "vocab"`, and `uv init` otherwise creates `src/vocab_coach/`.

**`authorize()` answers 404, not 403.** This is deliberate, so other users' IDs are not confirmed to exist. A test covers it.

## Next step: Language analysis

Read `PLAN.md` section "Language analysis" and, in `DESIGN.md`, the steps "analyse" and "a later conversation" under "One message through the system". Write the unit tests from "Done when" before the analyzer, then propose a plan and wait for approval.

Points to settle in that plan:

1. **Downloads need approval.** `uv run vocab setup-nlp` fetches the spaCy model `en_core_web_sm` and the NLTK `wordnet` corpus. Neither is installed yet, as far as I know; I did not confirm it. State the sources and sizes before running it.
2. **The frequency rule may be too broad.** The design marks any adjective or adverb with a Zipf frequency of 5.5 or more. Common function adverbs such as `not`, `so`, `then`, `also`, `just` and `too` are very frequent and may be tagged `ADV`, so they would be flagged in almost every sentence. I was about to check this with `wordfreq` when the session was interrupted, so it is unverified. Measure it on real sentences, and if it happens, add a small stoplist or skip negation and function-word adverbs, then record the change in `DESIGN.md` in the same change.
3. **Verbs only through the crutch list.** Otherwise `have` and `be` match everywhere.
4. **Spans.** Include an intensifier before an adjective (`really hard`, `very good`) and an adjective with its noun (`big problem`).
5. **Lemma matching.** Use spaCy's `PhraseMatcher` with `attr="LEMMA"` so `work around` matches `worked around`.
6. **Surface forms versus lemmas.** spaCy lemmatizes `data` as `datum`. Show surface forms to the user and use lemmas only for matching.
7. **Load spaCy once at startup**, not per request.
8. **Persistence.** The tables for `messages.word_count` and `message_lemma_counts` arrive in "Conversation UI", so for now test the analyzer output only.

The two checks in "Done when" are concrete: the migration sentence must mark `really hard`, `big problem` and `fixed` and must not mark `migration`, `data` or `had`, and `We worked around it` with learned option `work around` must return one hit.

## Rules to keep following

These are the ones most likely to be broken by accident. The full list is in `CLAUDE.md`.

- Every table holding user data has an indexed `user_id`, and every query on it filters by `user_id`.
- IDs are UUIDv4 strings generated in Python. Use SQLAlchemy only, with the generic `JSON` type.
- Never add a setting or flag that skips authentication. Tests use `app.dependency_overrides`.
- Only `src/vocab/llm/` may import `litellm`. A test for this arrives with the LLM client section.
- Add packages with `uv add` and install with `uv sync --locked`. Do not upgrade anything unless asked.
- User-facing text and documentation use plain sentences and no em dashes.
- A section is done only when its "Done when" checks have been run, `pytest` and `ruff` pass, new behaviour has tests, and the `PLAN.md` boxes are ticked. Design changes go into `DESIGN.md` in the same change.

## Symptoms and causes

| What you see | Cause |
|---|---|
| authentik redirects back with `invalid_request` | The provider's `grant_types` is empty. Check the blueprint |
| The authentik admin dashboard has no `vocab-coach` application | The blueprint failed validation. Read the worker log for `Entry invalid` |
| Logging out of the app and visiting it again logs you straight back in | The provider uses `default-provider-invalidation-flow` instead of `default-invalidation-flow` |
| The app crashes on start with "SESSION_SECRET is empty" | The root `.env` is missing or has no `SESSION_SECRET` |
| `pytest` fails on import with the same message | `os.environ.setdefault("SESSION_SECRET", ...)` in `tests/conftest.py` no longer runs before the `vocab` imports |
| A new table is missing from an autogenerated migration | Its model module is not imported in `migrations/env.py` |
| `/auth/callback` returns 400 "Login failed" | authentik refused the request or the login state expired. The reason is in the response text and in the authentik server log |
