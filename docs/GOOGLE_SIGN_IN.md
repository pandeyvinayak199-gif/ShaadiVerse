# Enable Google sign-in for ShaadiVerse

The app code uses Google through Supabase Auth. No Twilio number, SMS subscription or Google Cloud billing setup is required for ordinary Google OAuth sign-in. Supabase free-plan usage limits still apply. This change does not buy or upgrade any plan.

Your addresses:

- App: `https://shaadi-sync-demo.onrender.com`
- Supabase project: `https://oyluxvnfhchlogufsyaj.supabase.co`
- Google → Supabase callback: `https://oyluxvnfhchlogufsyaj.supabase.co/auth/v1/callback`
- Supabase → app callback: `https://shaadi-sync-demo.onrender.com/auth/callback`

## 1. Create the Google OAuth client

Open [Google Cloud Console](https://console.cloud.google.com/) and create or select your project. Open **Google Auth Platform** (older consoles may use APIs & Services → OAuth consent screen / Credentials).

Set the app branding to ShaadiVerse, choose your support and developer contact email, and choose an External audience for accounts outside your organisation. For initial Testing, add the Google accounts you will use as test users. For a public launch, change the audience/publishing status as instructed by Google; follow any verification prompts shown for your project.

Under **Clients**, create an OAuth client with application type **Web application**. Add this exact **Authorised redirect URI**:

```
https://oyluxvnfhchlogufsyaj.supabase.co/auth/v1/callback
```

Use the standard sign-in scopes: openid, email and profile. Save the Client ID and Client Secret. Do not put the Client Secret in chat, browser JavaScript or Git.

## 2. Enable Google in Supabase

Open [your Supabase project](https://supabase.com/dashboard/project/oyluxvnfhchlogufsyaj). Under **Authentication → Sign In / Providers → Google** (sometimes labelled Providers), enable Google. Enter the Client ID and Client Secret from Google, then save. Leave advanced security options at their defaults.

Under **Authentication → URL Configuration**, set:

- Site URL: `https://shaadi-sync-demo.onrender.com`
- Redirect URLs: add exactly `https://shaadi-sync-demo.onrender.com/auth/callback`

The two callback URLs above are different on purpose. Google's client redirects to Supabase; Supabase redirects back to the app.

## 3. Configure Render

In the existing Render service → Environment, set:

| Variable | Value |
|---|---|
| `APP_MODE` | `user` |
| `AUTH_PROVIDER` | `google` |
| `SUPABASE_URL` | `https://oyluxvnfhchlogufsyaj.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Your project's publishable key from Supabase project settings → API Keys |
| `PUBLIC_BASE_URL` | `https://shaadi-sync-demo.onrender.com` |
| `COOKIE_SECURE` | `1` |
| `TRUST_PROXY` | `1` |

A legacy public anon key may instead be supplied as `SUPABASE_ANON_KEY`. Do not use the service-role key. Keep the existing `DATABASE_URL` unchanged; the database connection and Auth configuration are separate. Twilio settings are not needed by this sign-in flow. Google Client Secret belongs in Supabase's Google provider settings, not this app's frontend.

Save, then select Manual Deploy → Deploy latest commit. Additive private database tables are created automatically. Open the app in Safari or Chrome and choose Continue with Google. Until these settings and provider consent are enabled, sign-in cannot be live-tested; the app clearly shows setup is pending when its local settings are missing.

## Invitations and existing accounts

Invite guests and team members using the exact email they use to sign in with Google. Contact phone numbers remain optional and are never used as proof of Google identity. The owner may approve a signed-in guest's request using the invitation code. Revoked access stays revoked across sign-outs and future sign-ins.

Existing phone-created weddings are preserved, but they are not silently assigned to a Google account based on a typed phone number or matching display name. If you already have real phone-based accounts, arrange an explicit, verified account migration with the app administrator before switching those users. Existing verified sessions remain valid until their normal expiry. `AUTH_PROVIDER=phone` is an optional legacy compatibility setting for the server; the standard user interface now uses Google.

## Security and tests

The server keeps the PKCE verifier and exchanges the returned code with Supabase. It validates the authenticated Supabase user and verified Google identity, then issues its own HttpOnly app cookie. Access and refresh tokens are not saved in browser storage or the app database. Login attempts expire after ten minutes, are bound to a browser cookie, and are consumed once. App sessions expire normally, and wedding permissions are checked from the database.

Automated tests use mocked provider responses and redirects. They verify callbacks, identity validation, invitation grants, revocation and account isolation. They do not log into a real Google account, configure Google/Supabase consoles or claim to test a live consent screen. Complete one real sign-in with a configured Google test user before inviting customers.
