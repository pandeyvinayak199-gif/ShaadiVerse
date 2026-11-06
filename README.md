# ShaadiVerse · Investor & Pilot Edition 1.0

The current release is an isolated, sample-data investor demonstration with a guided walkthrough, role switching, reset, consent-based pilot survey, and connect-later checklists. SMS, WhatsApp and payments are deferred.

- **Connect your existing Supabase project to Render:** [step-by-step guide](docs/CONNECT_SUPABASE.md). A ChatGPT plugin connection alone does not connect hosting.
- **Present and run a pilot survey:** [five-minute demo guide](docs/INVESTOR_DEMO.md).
- **Optional new-service blueprint:** [Render + existing Supabase](deploy/render-supabase-demo.yaml). This provisions no paid database.


A mobile-first wedding planner with event-isolated accounts, guest RSVP, a timeline, vendors, expenses, signed QR entry, team permissions, and live-service adapters. The existing hosted free demo remains a sandbox.

## Run locally

Python 3.12+:

```sh
python -m pip install -r requirements.txt
DEMO_MODE=1 python server.py
```

Open the server on port **3000**. `DEMO_MODE=1` seeds Rahul & Priya only when the database is empty and explicitly enables sample-role sign-in and visible sandbox OTPs. Each browser visitor gets a separate sample wedding. Switch roles within that workspace and create additional fictional events from the event switcher. Public demo phone sign-in is disabled. Developers may explicitly set `ALLOW_SANDBOX_OTP=1` only for isolated authentication testing; **never treat that OTP as verified phone ownership.**

For verified-user mode, use `DEMO_MODE=0` (the default), configure Twilio Verify, and use persistent storage. Live mode disables demo roles, does not return OTPs, and rejects sessions issued in sandbox mode. App tables use the private `shaadi_sync` PostgreSQL schema with RLS and anonymous access revoked; recognised legacy app tables are migrated transactionally. No database password or provider key is exposed by the connection checklist. The server reads process variables; `.env.example` documents names but is not automatically loaded. Enter credentials in hosting settings, never in Git or chat.

## What is now implemented

- **Storage:** additive migration of the existing SQLite data; WAL and transactional writes; durable hashed sessions, expiring OTP challenges, attempt limits, account and event memberships, audit records, payment orders and a message outbox. SQLite can use a mounted disk; `DATABASE_URL` selects PostgreSQL. PostgreSQL transactions and row locks protect admission and finance limits.
- **Accounts:** real Twilio Verify adapter, India +91 mobile normalization, single-use verification, resend/attempt limits, 24-hour sessions, logout invalidation, HttpOnly/SameSite cookies, production Secure-cookie setting, JSON/Origin/CSRF checks. Render blueprints enable trusted-proxy client identification for IP limits; leave `TRUST_PROXY=0` for direct local access. No caller-selected role in live mode.
- **Events:** verified users create events, switch among their own memberships, share real invitation URLs, regenerate codes, approve join requests and revoke access. Codes never reveal guest records. Staff permissions are assigned by the organiser; finance is capped at five members. Vendor/hotel accounts are bound to one linked entity. Pre-registered guests join only after verifying their own phone.
- **QR:** signed, unguessable, revocable passes rendered by a pinned QR library; guest-private QR download; camera decoding with bundled MIT-licensed jsQR; transactional duplicate and plus-one checks; staff logs and request idempotency. Offline scans are **pending**, not approvals, until the server confirms them. The service worker caches the application shell, not guest/API/pass responses. Pending scans are scoped to the current account/event and cleared on logout.
- **WhatsApp:** consent-gated invitation-template queue, explicit user-triggered dispatch, delivery webhooks, signed/context-bound Yes/No/Maybe RSVP callbacks, failure review and webhook replay protection. Sandbox mode sends nothing.
- **Payments:** server-priced Razorpay Event Pass checkout (₹2,999 per event), order records, checkout signature and captured-payment validation, signed webhooks, idempotent activation, a payment receipt, and Free-plan limits. A Free event supports 50 guests, invitations, RSVP and timeline; vendor/expense/QR features use Event Pass. Guests always keep access to their invitation and RSVP. No payments occur in demo mode.
- Existing dashboard, responsive light/dark UI, themes, countdown, guest CSV, timeline, tasks, travel milestones, catering, gifts, songs and polls remain available.

## Keep the free demo

The root `render.yaml` still uses a **free** web service. Set `DATABASE_URL` in Render to use your persistent Supabase database; without it, the local fallback is ephemeral. It now installs the QR and PostgreSQL dependencies. It keeps demo mode, password protection and manual deployment, and explicitly disables unverified sandbox phone sign-in. No paid plan is activated by this repository change. The Render-generated `DEMO_ACCESS_PASSWORD` protects the optional demo with username `demo`.

To update that demo after code is pushed, use Render’s **Manual Deploy → Deploy latest commit**. The web service may sleep. Without `DATABASE_URL`, local sample edits and survey answers may be lost on restart. With Supabase, the stored data follows that database’s persistence/backup policy. The demo is intended for fictional event data and concept surveys, not production guest identity verification.

## Permanent storage: choose later

Both options are prepared; neither was purchased or activated:

1. **Render disk:** `deploy/render-disk.yaml` describes a separate **paid starter** service with a 1 GB disk at `/var/data`. The database is `/var/data/shaadi.sqlite3`; demo mode is off. Import this blueprint only after deliberately choosing the paid service. Disk persistence is separate from backups. Keep one application instance for this SQLite configuration.
2. **Existing PostgreSQL:** `deploy/render-postgres.yaml` uses a free web service with a database you supply separately through `DATABASE_URL`. It does not buy or create a database. Durability, expiration and backups depend on your chosen provider. Remote connections require `sslmode=verify-full`, using system certificate trust by default; supply the appropriate trusted CA through libpq settings for a private CA. Loopback development databases may omit TLS.

Run `python manage.py check` against the intended configured database before use. SQLite migrations/backups and real local PostgreSQL migrations, private schema/RLS, session/survey restart persistence and concurrent admission are tested. Your actual Supabase connection still requires the secure Render setting; no external Supabase project was accessible in this workspace.

### Preserve data and back up

Existing SQLite records are migrated in place; they are not reset. Legacy demo sessions were memory-only and must sign in again. Legacy seeded data does not grant unverified users organiser access in live mode.

```sh
DATABASE_PATH=/var/data/shaadi.sqlite3 python manage.py backup /secure/location/shaadi-backup.sqlite3
```

This uses SQLite’s online backup API, validates the result and refuses overwrites. Backups contain personal data and signing/session information. Keep them private and copy them outside the service disk. For PostgreSQL, use provider-managed backups or `pg_dump`; the SQLite backup command does not pretend to back up PostgreSQL. To move an existing SQLite application to a disk, back it up first, stop writes, place the intact backup at the new `DATABASE_PATH`, then start and run `manage.py check`. Do not delete the source until independently verified. Importing an existing SQLite dataset into PostgreSQL requires a separate data migration; changing `DATABASE_URL` alone does not copy records.

## Connect real services

No live credentials are currently supplied, and provider delivery/capture has not been live-tested. Missing configuration returns an explicit unavailable response; there is no silent mock fallback. Use service test/sandbox accounts first and perform an authorised real-device smoke check before inviting guests.

### Phone OTP: Twilio Verify

Configure `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_VERIFY_SERVICE_SID`. Enable SMS to India in your Twilio account, including any sender, destination, trial-recipient or regulatory approvals your account requires. Set `DEMO_MODE=0`, `COOKIE_SECURE=1` and `PUBLIC_BASE_URL` to your HTTPS app URL. Sign-in and event creation then use verified phone ownership. Only India (+91) numbers are currently supported.

### WhatsApp Cloud API

Configure `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_TEMPLATE_NAME`, `WHATSAPP_TEMPLATE_LANGUAGE`, `WHATSAPP_APP_SECRET`, and an independently chosen `WHATSAPP_VERIFY_TOKEN`.

Approve a Meta invitation template whose body has exactly three text parameters, in order: **guest name**, **event name**, **event code**. For a template with three quick-reply buttons (Yes, No, Maybe), set `WHATSAPP_RSVP_BUTTONS=1`; the adapter supplies the payloads `RSVP_YES`, `RSVP_NO`, `RSVP_MAYBE`. Configure the webhook as `https://YOUR-APP/api/webhooks/whatsapp`, with the verify token, and subscribe to messages. Callback signatures are checked against the app secret; RSVP replies must reference an outbound provider message and match its recipient.

Guests explicitly opt in during RSVP and can opt out on a subsequent RSVP. Organisers select eligible recipients and queue invitations, then review and explicitly send up to 20 at a time in Settings. Failed or uncertain deliveries need provider-log review; they are not automatically retried. No automated reminder scheduler or arbitrary free-text broadcasts are included in this release. WhatsApp provider charges can apply when you explicitly dispatch.

### Razorpay

Configure `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` and a separate `RAZORPAY_WEBHOOK_SECRET`. Start with Razorpay **test mode**. Configure `https://YOUR-APP/api/webhooks/razorpay` for `payment.captured`. Checkout callbacks activate a plan only after fetching and matching a captured payment; signed captured webhooks provide recovery if the browser closes. Editing the event cannot change its paid plan.

₹2,999 is the current server catalog price in `server.py`, in paise. Review your business pricing before connecting live keys. The downloadable document is a **payment receipt**, not a GST tax invoice. Seller GST/billing configuration, Planner Pro recurring subscriptions, refunds/cancellations and marketplace payouts are not implemented. Razorpay/provider account activation and live capture still require account-side setup and testing.

## Validation

```sh
python -m unittest discover -s tests -v
node --check static/app.js
node --check static/features.js
```

Integration tests use disposable SQLite databases, explicit sandbox mode or mocked live providers, and no real messages/charges. They exercise data isolation, authentication/CSRF, OTP limits, staff scopes, migration, backups, capacity limits, tampered/revoked QR passes, concurrent duplicates, offline request idempotency, payment amounts/signatures/capture/webhook replay and WhatsApp consent/callbacks.

Optional browser validation (Playwright and Chromium required):

```sh
# Start an isolated sample instance in a separate terminal:
DEMO_MODE=1 DATABASE_PATH=/tmp/shaadi-browser.sqlite3 PORT=3001 python server.py
APP_URL=http://127.0.0.1:3001 node tests/browser-investor.cjs
APP_URL=http://127.0.0.1:3001 node tests/browser-features.cjs
```

Use a fresh disposable database for each browser run: the browser tests create sample events, assign a fictional team member, submit a consented survey and check in sample guests. `CHROMIUM_PATH` overrides `/usr/bin/chromium`. This validates actual SVG encoding/decoding, mobile layout, online/duplicate/offline gate states, sync, isolated visitor workspaces, demo event creation and invitations. Camera hardware permissions and real provider delivery still require device/account checks.

## Remaining original-brief work

These five recommended upgrades are implemented in code and need the hosting/provider activation described above. This is still not every feature in the much larger original brief: seating drag-and-drop, ID/contract/receipt uploads, per-guest hotel-room assignments, automatic personal-data deletion, Hindi translations, memory books, invitation animation, planner subscriptions, platform admin and marketplace features remain separate work. Offline scanning intentionally does not claim multi-device admission authority while disconnected.

## Local PostgreSQL validation

The optional `tests/test_postgres.py` creates and drops only randomly named test databases on a disposable PostgreSQL server that you explicitly supply via `TEST_DATABASE_URL`; it requires CREATEDB privileges and must not point at a production service. The normal SQLite suite skips these four tests when no test server is supplied. Actual local PostgreSQL validation covers private-schema/RLS access, preserved legacy tables, survey/session persistence across initialization and concurrent duplicate gate checks. This does not verify the live Supabase account.

## Walkthrough startup checks

The walkthrough waits for the sample dashboard before opening, disables duplicate starts while loading, and leaves a visible retry message if loading fails. All presentation handlers are installed before bootstrap. Dashboard records share one database connection per response, and PostgreSQL sample inserts are batched. To exercise delayed loading and failure recovery, run `APP_URL=http://127.0.0.1:3004 node tests/browser-walkthrough.cjs` against a disposable demo instance.

## Install on Android or iPhone

ShaadiVerse now includes a standalone PWA manifest, 192/512 px and maskable app icons, an Apple home-screen icon, safe-area spacing and an in-app installation entry. Android uses the native browser prompt when available; iPhone users receive Safari Add to Home Screen instructions. See [phone installation](docs/INSTALL_ON_PHONE.md). The browser fallback remains available on desktop.

`node tests/browser-pwa.cjs` checks manifest installability with a disposable normal Chrome profile (Incognito cannot install apps), installation UI, iPhone guidance, offline launch and exclusion of private API responses from the cache. Supply `APP_URL` and optionally `CHROMIUM_PATH`. The native OS installation itself needs a real-device check.

## Spotify song links

In Celebrations, organisers and guests can add a song name, optional artist and optional Spotify track/share link. Saved track links open Spotify in a separate tab/app; requests without a URL receive a Spotify search link, including older song records. Organisers can edit a song’s link later. Guest requests retain Pending status and guests see their own requests. HTTPS Spotify track links, official `spotify.link` shares and track URIs are accepted and normalised; no Spotify API credentials, automatic track matching or embedded playback are used.

## Memories shared photo albums

**Memories → Create our Memories album** gives each event a guest QR/link and a separate private host link. Guests enter a name, upload multiple photos, browse everyone’s photos and download individual images or a selected ZIP. Photos use the existing private database, including Supabase when configured; no new service credentials are needed. JPEG/PNG/WebP/HEIC uploads are validated, optimised for sharing and stripped of original location metadata. Finite storage/file-size limits are explicit. Hosts can pause uploads/access, rotate guest links and remove photos. See the [Memories guide](docs/MEMORIES.md), especially saving the private host link before resetting a demo.

### Help box

The floating **✧ Help** button provides built-in app guidance for guests and organisers. Optional live AI can be enabled with a server-side OpenAI key; see [AI help setup](docs/AI-HELP.md).
