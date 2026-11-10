# ShaadiVerse

A mobile-first wedding planner that starts with your own wedding. New users sign in with Google, create a wedding, and add their guests, functions, budgets, vendors, hotels, transport, catering, songs and memories from scratch. There are no sample weddings, role-switching demos, pilot surveys or presentation prompts in the user app.

Short, contextual guidance can be dismissed with one tap, turned off, and reopened from Settings or the planning guide. The installed phone experience uses the same Google account and saved wedding data as the website.

## Run and deploy

Python 3.12+:

```sh
python -m pip install -r requirements.txt
APP_MODE=user python server.py
```

Open port 3000. The server reads process environment variables; `.env.example` documents them and is not loaded automatically. Configure credentials in hosting settings, never in Git or chat.

Before opening sign-ups, enable Google in Supabase and configure the app's Supabase Auth URL and publishable key. See [your exact Google/Supabase/Render setup steps](docs/GOOGLE_SIGN_IN.md). Google replaces phone OTP in the user interface, so no SMS provider is required. Automated tests mock Google provider responses; the real Google consent flow still needs the external console settings and a real test-user sign-in.

Set `COOKIE_SECURE=1`, `TRUST_PROXY=1` behind Render's trusted proxy, and `PUBLIC_BASE_URL` to the HTTPS app URL. Set `DATABASE_URL` securely in Render to the existing Supabase PostgreSQL connection. See [Supabase connection instructions](docs/CONNECT_SUPABASE.md). The root Render blueprint runs the real-user app; the existing service can use Manual Deploy → Deploy latest commit.

`APP_MODE=user` is the default. Legacy `DEMO_MODE`, `ALLOW_SANDBOX_OTP` and `DEMO_ACCESS_PASSWORD` values alone cannot enable samples, unverified sign-in or a demo password gate. Remove obsolete demo variables from hosting settings when convenient. Explicit `APP_MODE=test` is reserved for isolated regression fixtures and must never be used on the live service.

## Fresh wedding data and migration

New weddings contain only the name, date and optional venue, hashtag and budget entered by their organiser. Functions are not pre-created, and guest, hotel, vendor, expense, transport, catering, task, poll, song and memory lists start empty. New personal weddings have the Wedding plan, making the existing planning features available without the old sample-plan checkout. Legacy paid purchases remain unchanged.

On real-user startup, records marked `demoWorkspace` are removed, together with their sessions, memberships, invitation codes, sample photos, audio and related records. The recognised legacy sample is identified by its original code and lack of real owner membership before marking. Cleanup never matches weddings merely by couple name. Real weddings and their accounts are preserved, even when they share the sample couple's name. Sandbox sessions are invalidated. Back up your database before deployment so the retired sample data can be recovered if you need it.

Use persistent storage: Supabase PostgreSQL or a mounted SQLite volume. A free Render service's local filesystem is temporary and is unsuitable for durable wedding records. Remote PostgreSQL requires verified TLS; use the provider's trusted certificate configuration. Application tables live in the private `shaadi_sync` schema with row-level security and anonymous privileges revoked.

```sh
python manage.py check
DATABASE_PATH=/var/data/shaadi.sqlite3 python manage.py backup /secure/location/shaadi-backup.sqlite3
```

SQLite backups use the online backup API and refuse overwrites. For PostgreSQL use provider-managed backups or `pg_dump`, including the `shaadi_sync` schema. Changing `DATABASE_URL` does not copy data between databases.

## Features and setup

- [Guest families, per-function RSVPs, hotel requests and vendor payment records](docs/GUEST-PLANNING.md)
- [QR-shared Memories albums and private photo storage](docs/MEMORIES.md)
- [Private song mashup uploads and playback](docs/SONG-MASHUPS.md)
- [Install on a phone](docs/INSTALL_ON_PHONE.md)
- [Help box and optional live AI setup](docs/AI-HELP.md)

Owners invite co-organisers and finance members with event-scoped permissions. Guests sign in using their invited Google email and see their own family and song requests, the full function schedule, and public choices for booked hotels. Co-organisers set guest and room-request limits according to their permissions. Signed QR entry is validated by the server; offline scans remain pending until synchronised.

Optional WhatsApp and Razorpay settings are listed in `.env.example`. Invitation dispatch requires opted-in guests and an approved WhatsApp template. Vendor payment preparation uses a UPI handoff and separate, clearly labelled manual transaction recording. Razorpay vendor transfers remain deferred and require an appropriate Route/payout integration; ordinary Checkout keys alone do not pay vendors. No automated external messages or charges are triggered by deployment.

## Verification

```sh
PYTHONPATH=. python -m unittest discover -s tests -q
```

Tests use isolated databases and explicit test fixtures. Production first-run tests verify blank accounts, no sample records, Google identity enforcement (and optional legacy phone compatibility) and safe cleanup. Optional PostgreSQL tests require an explicitly supplied disposable `TEST_DATABASE_URL`; they create and drop only randomly named test databases. Browser tests include a full first-use flow in `tests/browser-fresh-start.cjs`, using an isolated app whose SMS adapter is mocked. Old presentation-only browser scripts are retired and do not describe the user app.

### Google sign-in browser check

For a local test that sends no SMS and uses no real Google account:

```sh
python tests/serve_google_fixture.py --allow-mocked-auth
# In a second terminal:
node tests/browser-google-auth.cjs
```

This fixture binds localhost, uses a fresh temporary SQLite database and mocks only provider responses. Never deploy the fixture script. The production server always verifies Google sign-in with Supabase over HTTPS. A real Google test-user consent check remains necessary after configuring the external accounts.
