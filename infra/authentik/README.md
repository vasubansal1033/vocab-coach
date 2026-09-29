# authentik for vocab-coach

authentik is the login provider. It runs from the official Compose file (image tag pinned in `compose.yml`). It needs about 2 CPU cores and 2 GB of RAM. The app and authentik keep separate databases.

The worker container mounts the Docker socket. That is part of the official file (authentik uses it to manage outposts). Remove that line if you never use outposts.

## Start it

`infra/authentik/.env` already holds a generated `PG_PASS` and `AUTHENTIK_SECRET_KEY`. It is git-ignored. To regenerate on a fresh checkout:

```bash
printf 'PG_PASS=%s\nAUTHENTIK_SECRET_KEY=%s\n' "$(openssl rand -base64 36 | tr -d '\n')" "$(openssl rand -base64 60 | tr -d '\n')" > infra/authentik/.env
```

```bash
docker compose -f infra/authentik/compose.yml up -d
```

Changing the secrets after the first start breaks the existing database, so do not regenerate them on a running install.

## What is automated

`blueprints/vocab-coach.yaml` is mounted into the worker at `/blueprints/custom`. authentik applies it on start and whenever the file changes. It creates:

- the OAuth2/OpenID provider `vocab-coach` (confidential, RS256, scopes `openid email profile`) with the strict redirect URI `http://localhost:8000/auth/callback`;
- the application with slug `vocab-coach`;
- the `default-enrollment-flow` sign-up flow, and a "Sign up" link on the login page (the identification stage points at it).

The client ID and secret come from `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET` in `infra/authentik/.env`. Put the same two values in the repo-root `.env`. Both files are git-ignored. To make new ones, generate them with `openssl rand -hex 20` and `openssl rand -hex 64`, update both files, then `docker compose -f infra/authentik/compose.yml up -d`.

## What you still do by hand

- [ ] Set the `akadmin` password at <http://localhost:9000/if/flow/initial-setup/>. Only needed to use the admin UI at <http://localhost:9000/if/admin/>; the app does not need it.
- [ ] Sign up your own user at <http://localhost:8000/> (the "Sign up" link on the login page). You choose the password.
- [ ] Check the repo-root `.env` has `SESSION_SECRET`, `OIDC_ISSUER` (with trailing slash), `OIDC_CLIENT_ID` and `OIDC_CLIENT_SECRET`.

If the application is missing from the admin dashboard, read the worker log for `Entry invalid` or `Blueprint validation failed`:

```bash
docker compose -f infra/authentik/compose.yml logs worker | grep -E "Entry invalid|validation failed"
```

## Troubleshooting

| What you see | Cause |
|---|---|
| authentik error page about the redirect URI | The URI in step 6 differs from `http://localhost:8000/auth/callback` in scheme, host, port or path |
| Discovery returns 404 | The application slug is not exactly `vocab-coach`, or `OIDC_ISSUER` lacks its trailing slash |
| Logging in to one side logs you out of the other | Both sides share the `localhost` cookie jar. The app uses the cookie name `vocab_session` to avoid this |
| `docker compose` says a variable is required | `infra/authentik/.env` is missing `PG_PASS` or `AUTHENTIK_SECRET_KEY` |
