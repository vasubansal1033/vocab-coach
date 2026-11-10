# App Postgres

Separate from authentik's Postgres. The app database holds conversations, events, and the lexicon.

## Local

```bash
cp .env.example .env   # set POSTGRES_PASSWORD
docker compose -f infra/postgres/compose.yml --env-file infra/postgres/.env up -d
```

Point the app at it:

```bash
DATABASE_URL=postgresql+psycopg://vocab:YOUR_PASSWORD@localhost:5432/vocab
uv run alembic upgrade head
psql "$DATABASE_URL" -f infra/postgres/rls.sql
```

## Copy from SQLite

```bash
uv run vocab db copy-sqlite --sqlite sqlite:///./data/app.db --postgres "$DATABASE_URL"
```

Run Alembic on Postgres first so tables exist, then copy, then apply `rls.sql`.

## Row-level security

`rls.sql` turns on RLS for every table with `user_id`. The app sets `app.current_user_id` on each Postgres connection through `set_pg_user_context()` so policies can filter. Owner checks in `authorize()` remain the first line of defence.
