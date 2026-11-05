# ShaadiVerse 1.0 — investor demonstration and concept pilot

This release is the fixed demo scope for the current stage. It demonstrates the product; it is not a claim that the entire original production brief or live provider onboarding is complete.

## Before the meeting

- Deploy the latest commit in Render and connect Supabase using [the connection guide](CONNECT_SUPABASE.md).
- Open your HTTPS app URL a few minutes early so the free web service wakes up.
- Use your existing private demo password if configured. Don’t share infrastructure credentials with visitors.
- Choose **Take the five-minute walkthrough**. Each new browser sign-in creates its own sample wedding. Role switching keeps that same workspace; “Start fresh” opens a new sample wedding for another presentation.
- Keep the fictional sample-data notice visible. Demo guest counts, votes, expenses and vendor payments are sample records, not business traction.

## Five-minute story

1. **The problem:** weddings involve many people, messages and moving parts. Show the home screen and the countdown.
2. **The guest story:** open Guests; search, add a fictional guest, edit RSVP/dietary data and show a confirmed guest’s signed QR pass.
3. **The photo story:** open Memories, create an album, show the guest QR and explain name-only sharing, uploads and downloads. Save the separate private host link.
4. **The coordination story:** show Timeline, Tasks, Travel & stay and Catering.
5. **The trust story:** show Expenses, approval status, member permissions and revocation. Switch to Guest to demonstrate the private passport without finance or other guests’ records.
6. **The pilot:** open the survey, explain the explicit consent, and collect ease-of-use, usefulness, willingness-to-use, respondent perspective and optional comments. Responses are stored, not fabricated.

“Present” expands the organiser dashboard for a screen share; “Exit presentation” restores the navigation. The six-step walkthrough is also available inside the demo strip.

## Pilot procedure

Share the app URL and demo access password, if configured. Ask participants to use fictional people and event information. Each participant can explore roles and create a sample event without needing an SMS provider or making a payment. The public demo does not expose fake phone verification as real account authentication.

After trying the product, participants choose **Share pilot feedback**. Consent is required. A repeat submission from the same workspace updates its existing response; a fresh workspace may produce another response, so report **responses**, not unique users. Feedback is private to the app/database operator and persists in Supabase after the database is connected. Offline surveys are not silently saved; reconnect and submit successfully.

## Deferred services

Use **Connections · Set up later** for Supabase, Twilio, WhatsApp Business and Razorpay checklists. This screen shows setting names and provider dashboard links, never stored credential values. Configure providers securely in hosting settings later. No live messages, identity-verification claims or charges occur in demo mode.

Supported now: QR-linked shared photo albums, guest CRUD/CSV/RSVP, timeline, vendors, expenses, tasks, travel milestones and room-block summaries, catering, gifts, songs, polls, event creation/switching, member restrictions, signed QR entry and explicit pending offline scans. Room assignments, ID uploads, memory books, seating planner, multilingual UI, production retention jobs, recurring subscriptions and marketplace features from the original larger brief are outside this demo release. Don’t describe them as shipped.
