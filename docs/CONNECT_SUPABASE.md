# Connect your existing Supabase project to your existing Render app

A ChatGPT plugin connection does not connect the running Render app. The app needs the PostgreSQL database URL in **Render’s settings**, not in this chat or a repository file. No live Supabase credentials or Render administration access were available to the coding workspace, so the actual account connection has not been performed here.

1. In your **Supabase project**, click **Connect** and choose the PostgreSQL **Session pooler** connection string. A pooler works with IPv4 hosting, including Render. Use the complete `postgresql://...` connection string, not the public project API URL or an anon/service-role API key.
2. Replace the password placeholder with your database password. If typing into a URL manually, percent-encode special characters in the password. Keep the string private.
3. In **Render → your existing web service → Environment → Add environment variable**, enter the name **`DATABASE_URL`** and paste the complete connection string as the value. Save it there; do not send it in chat.
4. Keep **`DEMO_MODE=1`**, **`ALLOW_SANDBOX_OTP=0`**, and **`COOKIE_SECURE=1`**. Keep your existing `DEMO_ACCESS_PASSWORD` if you want a password-protected presentation. You do not need Twilio, WhatsApp or Razorpay for this demo.
5. Choose **Manual Deploy → Deploy latest commit** after the updated code is on GitHub. On startup the app creates/migrates its own private schema transactionally. If startup fails, inspect Render Logs; do not paste database URLs or passwords into logs/chat.
6. Open the app, enter the organiser demo, and select **Connections · Set up later**. Storage should show **Supabase / PostgreSQL · Database query verified**. Submit a test pilot survey, restart the Render service, and confirm it remains in Supabase using the private query below.

## TLS certificates

TLS verification stays enabled. Remote connections use `sslmode=verify-full`; do not disable verification to make a connection pass. If your Supabase project requires a downloaded root certificate, download it from its database/SSL settings, add it as a Render secret file named `supabase-ca.crt`, and set `PGSSLROOTCERT=/etc/secrets/supabase-ca.crt`. Otherwise leave the default system CA trust. The client supports poolers and disables prepared-statement caching for pooler compatibility.

## Data privacy

App tables live in **`shaadi_sync`**, not the public API schema. Row-level security is enabled with no anonymous access policies; access is through the server’s authorised, event-scoped API. Don’t add this schema to Supabase’s exposed schemas or give public API users table privileges. The server-side database connection must be a role authorised to own and migrate this application schema. Never place the database URL or a service-role key in browser JavaScript.

Recognised legacy Shaadi Sync public tables are moved transactionally to the private schema. Unrelated project tables are untouched; ambiguous overlapping app tables cause migration to stop instead of overwriting data. Connecting a new PostgreSQL database does **not** copy an old SQLite file. The existing fallback SQLite demo is sample data; back up any wanted data before changing its storage.

## View real pilot feedback privately

As the project owner, use **Supabase → SQL Editor**:

```sql
select source, rating, usefulness, willingness, persona, comments, created, updated
from shaadi_sync.feedback
order by updated desc;
```

These are actual submitted survey answers. Do not present them as paying customers or unique people; a fresh demo workspace can submit a separate response. No contact details are requested, and commenters are told not to include personal information. Restrict access to the research team.

Aggregate research readout:

```sql
select count(*) as responses,
       round(avg(rating)::numeric, 2) as average_ease_of_use,
       round(avg(usefulness)::numeric, 2) as average_usefulness,
       count(*) filter (where willingness = 'Yes') as would_consider_using
from shaadi_sync.feedback;
```

A service operator with a shell can alternatively run `python manage.py feedback-export /secure/path/pilot-feedback.csv`. It refuses overwrite, writes a private file and escapes spreadsheet formulas. The export is not available to demo visitors.

The free Render web service can sleep; Supabase persistence, backups and project limits follow your chosen Supabase plan. No hosting upgrade or purchase is made by these files. A successful local PostgreSQL validation is not proof that your live Supabase account has been connected.
