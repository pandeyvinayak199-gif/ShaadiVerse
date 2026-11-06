# ShaadiVerse help box

Tap **✧ Help** on any app screen. Signed-in users can ask questions or tap suggestions. Guests receive guidance appropriate to their role. Help explains workflows; it cannot change wedding records or perform actions.

Built-in guidance works without an external account, including photo uploads, budget controls, RSVPs, songs, timelines and phone installation. The box clearly labels built-in answers.

## Optional live AI

In Render → Environment, add `OPENAI_API_KEY` using an OpenAI API project key. Keep it on the server. Do not commit it or paste it into chat. The optional `OPENAI_MODEL` defaults to `gpt-4.1-mini`; choose a model your API project supports. Save and redeploy. No database migration is needed. OpenAI API usage may be billed to that project; configure its budget and usage limits before enabling.

The server sends only the current question, the user's role, and the product help guide to OpenAI's Responses API. It does not attach wedding records, names, phone numbers, budgets, photos, or previous messages. Text users put into their question is sent, so the help box asks them to avoid sensitive details. `store: false` is sent to the provider; this does not replace the provider's own retention policies. The app does not save conversations to the database or browser storage; reopening the dialog clears them. Requests require sign-in and CSRF validation and are limited to 20 per account per hour. Removing the key returns to built-in guidance.

If the provider times out, rejects a key/model, or returns an empty answer, the box labels the problem and returns built-in guidance. Provider errors and keys are not returned to users. AI answers may be mistaken; important wedding details should be checked with the organiser. No live API request is needed for the automated tests; the provider contract and failures are tested with mocks.
