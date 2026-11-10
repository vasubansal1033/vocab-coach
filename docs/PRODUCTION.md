# Production checklist

Personal-phase deploy notes. Do these before exposing the app beyond your own machine.

## HTTPS and cookies

- Terminate TLS for the app and for authentik (reverse proxy or platform TLS).
- Set `APP_ENV=prod` so the session cookie is `Secure`.
- Keep `SESSION_SECRET` and OIDC secrets out of git; inject them from the host secret store.
- Set authentik redirect URI to the public `https://…/auth/callback` exactly.

## Database

- Prefer Postgres: `DATABASE_URL=postgresql+psycopg://…`
- Run `uv run alembic upgrade head`, then apply `infra/postgres/rls.sql`.
- To move an existing SQLite file: `uv run vocab db copy-sqlite --sqlite … --postgres …`

## Limits and privacy

- Set `LLM_RATE_LIMIT_PER_DAY` and `LLM_COST_LIMIT_USD_PER_DAY` for real traffic.
- Confirm `/about/privacy` matches the providers you actually call.
- Offer `/account/export` and `/account` deletion to the user.

## Licence review before any commercial launch

- Read authentik's enterprise licence under `authentik/enterprise/` in their repo.
- Read wordfreq's data terms (CC BY-SA and source credits) before redistributing frequency data.
- Keep `/about/attribution` accurate.

## Frontend

```bash
cd frontend && npm ci && npm run build
uv run uvicorn vocab.main:app --host 0.0.0.0 --port 8000
```
