# Connect the wedding app to Supabase

1. Open the existing Supabase project and copy its PostgreSQL connection details. Use a reachable session-pooler endpoint if the hosting network requires IPv4.
2. In Render, open the existing web service → Environment and add `DATABASE_URL` with the connection string and database password. Percent-encode reserved characters in passwords. Keep credentials out of chat, Git and screenshots.
3. Use verified TLS. The app defaults to `sslmode=verify-full` for remote PostgreSQL. If your provider requires a private CA, install its certificate on Render as a secret file and set `PGSSLROOTCERT` to its path. Do not disable certificate checks.
4. Set `APP_MODE=user`, `COOKIE_SECURE=1`, `TRUST_PROXY=1`, and `PUBLIC_BASE_URL` to the HTTPS app URL. Old demo environment variables can be removed; they do not activate samples in user mode.
5. Configure Google sign-in before sign-ups using [the Google setup guide](GOOGLE_SIGN_IN.md).
6. Back up the existing database, then deploy the latest Git commit. Startup removes only explicitly marked sample weddings and their files. Real weddings are preserved; new accounts and new weddings start blank.
7. Run `python manage.py check` against the configured database. Complete an authorised Google sign-in, create your own wedding, add a function, and confirm it remains after a service restart.

Application tables live in the private `shaadi_sync` schema. The app enables row-level security and revokes anonymous access. Do not expose the database password or service credentials in browser JavaScript. A plugin connection to Supabase does not automatically configure Render.

For PostgreSQL, use managed backups or `pg_dump` including `shaadi_sync`. Selecting a PostgreSQL URL does not import a previous SQLite dataset. Use a deliberate data migration when changing database engines. The existing audio and photo features store private bytes in the database; consider their combined allowances when monitoring project capacity.
