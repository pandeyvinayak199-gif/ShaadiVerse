# Shaadi Sync

A responsive, persistent wedding-planning **development prototype**, built with Python 3.12+ (standard library), SQLite, and plain JavaScript. No package installation, paid services, or credentials needed.

## Run

```sh
cd /workspace/ShaadiVerse
python server.py
```

The server listens on port **3000** (`PORT` overrides it). The first launch seeds Rahul & Priya's wedding. `DATABASE_PATH` overrides the SQLite file location. Visit the application in your local browser or your environment's supported preview. Choose **Explore Rahul & Priya’s wedding**, or select another demo role. Each HTTP request enforces role restrictions in the backend.

For registered guest OTP, use a seeded number such as `9000000000`. The sandbox generates a code and displays it in the verification dialog; no SMS is sent. This verifies the sandbox flow, **not real phone ownership**.

## Implemented

- Six demo roles: organiser, co-organiser, finance, vendor, guest, hotel partner.
- Seeded wedding dashboard, countdown, live-from-database headcount, upcoming celebrations, tasks, budget summary, responsive navigation, light/dark mode, RSVP confetti, local palace illustration.
- Guest creation/editing, search, side/status filters, quoted CSV import and CSV export.
- Guest-only RSVP with consent and plus-one limit validation.
- Event code join requests and organiser approval. Joining alone does not grant access. Regenerating the event code invalidates the old code.
- Sub-event timeline, venue map links, and dress codes.
- Vendor details and vendor-scoped API responses.
- Expense creation, finance cap enforcement, large-expense approval requirement, paid/outstanding summaries, CSV and print-to-PDF, database audit entries.
- Manual reference-based online gate check-in with duplicate detection and entry logging.
- Hotel room-block summaries, transport details, arrival board, catering plate comparisons, dietary counts.
- Editable tasks, private gift/shagun records and thank-you status/export, guest song requests, one-vote-per-user polls, hashtag ideas, shareable WhatsApp invitation URL.
- Explicitly labelled sandbox WhatsApp response and plan previews; no real messages or payments.
- Organiser-editable event details and five colour palettes, guest consent-based travel milestones, and restricted finance audit viewer.

## Validation

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

Tests use a separate temporary database and exercise authentication requirements, guest privacy, vendor scope, finance cap, approval threshold, join isolation, plus-one limits, duplicate entry detection, source-file disclosure prevention, travel consent, duplicate voting, audit privacy, and logout invalidation.

Optional browser checks (with Playwright installed and `/usr/bin/chromium` available): start the app, then run `node tests/browser-smoke.cjs`. Override `APP_URL` and `CHROMIUM_PATH` as needed. The smoke check saves the existing event name and changes the demo guest travel milestone to Left home. They require permission to open a loopback socket.

## Scope and production work still required

This is a first working prototype, **not the complete production specification**. It currently manages one seeded event. Event creation/multiple-event workflows, full co-organiser permission configuration, member-bound staff authentication, access revocation, real QR generation and camera/offline scanning, transfer approval, photo/ID/contract/receipt upload storage, room assignments, per-category budget editing, automatic reminders, seating drag-and-drop, memory book, invitation builder, Hindi translations, enforceable billing/plan gates, Razorpay, GST invoices, platform-admin metrics, partner marketplace models, and scheduled 30-day data deletion are not implemented.

Demo login deliberately permits choosing any seeded role. **Do not expose this server to untrusted users or store actual guest/ID information.** `DEMO_MODE=0` disables role switching, but does not make sandbox OTP production safe. Before deployment replace sandbox authentication with a verified SMS provider, bind users to event-scoped membership, use expiring durable sessions, secure cookies behind HTTPS, rate limits and CSRF protection, robust schema validation, transactional check-ins and approvals, migrations/backups, and a production application server.

Sessions expire after 24 hours and are invalidated on logout. Sessions and pending OTPs are memory-only; application data persists in SQLite. Processes must be restarted in a new environment. Use the existing checkout; no worktree is needed. No environment configuration was published or modified as part of this application build.
