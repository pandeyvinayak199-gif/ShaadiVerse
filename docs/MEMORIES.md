# Memories — one QR, everyone’s photos

## For the organiser

1. Deploy the latest commit in Render. Keep the existing `DATABASE_URL` and certificate settings. The build command must install `requirements.txt`; the new image libraries are included there.
2. Open your event and choose **Memories → Create our Memories album**.
3. Use **Download QR** to save/print the guest QR, or **Copy album link** to share it.
4. **Save private host link** somewhere only you can access. That separate link lets you manage this album from another phone or after the demo session expires. Do not print it or send it to guests.

There is one album per event. The shared QR opens that specific album without exposing guest records, finances, rooms or other events. The app’s existing private-demo password is not required for the shared album itself; guests need the unguessable album link and must enter a name and accept photo-sharing consent.

A fresh demo creates a different wedding/workspace. It does not delete photos from old albums. Keep the original guest QR and private host link for an album you want to keep using. Images live in the existing private SQLite/PostgreSQL database, not the temporary Render filesystem. With your Supabase connection they persist with that database; no Storage bucket or extra API key is needed for this pilot implementation.

## For A, B, C and D

- Scan the Memories QR with the phone camera, or open its link in a browser.
- Enter your name and accept sharing your name/photos with people who have the album link. A name is a photo credit, not a verified identity.
- Choose multiple photos and tap **Upload selected photos**. You can repeat this; there is no fixed per-person photo count. Successful and failed uploads are shown separately. Keep the page open to retry unsaved files.
- Everyone with album access can browse the same gallery. Tap **Browse photos** to jump to it, or **Refresh album** for new uploads. The first gallery page refreshes periodically when idle; large albums have **More memories** pagination.
- Use **Save photo** for an individual picture, or select photos and **Save selected as ZIP**. ZIP downloads allow up to 50 selected images / 50 MB per batch; repeat for more.
- On iPhone, downloads may go to Files. Open a photo and long-press it to save it to Photos if Safari offers that option.

Uploads use JPEG, PNG, WebP or HEIC. They are optimised to at most 2560 pixels on the longest side, saved as JPEG, and original EXIF/GPS information is stripped. Keep original files elsewhere if you need original resolution or metadata. Unsupported/corrupt files are rejected; large HEIC files that the browser cannot resize may need a smaller JPEG export.

## Album controls

- **Pause uploads:** people can still view and save existing pictures.
- **Pause shared access:** guests cannot open the gallery or retrieve images until sharing resumes. The host can still manage it.
- **Replace shared QR / link:** revokes the old QR and ordinary visitor sessions while retaining photos and host access. Share the newly generated QR afterwards.
- View a photo to remove it. Visitors can remove their own current-session uploads; the organiser can remove any photo. Removal does not erase copies people have already downloaded.

Treat the guest QR as an invitation to the album. Anyone who receives it can enter a name and access those photos, including forwarding the link. The private host link grants organiser control and must be kept separate. Only the event creator or an already authenticated private host receives it; co-organisers with photo permission get in-session controls without the permanent host secret. The creator can replace the private host link to revoke it and other host sessions while keeping the guest QR and photos unchanged. Visitor/host browser sessions expire after seven days; reopening the appropriate original link allows a new session. No phone number, SMS, WhatsApp or payment is required.

## Storage and operational limits

Physical storage is finite. The pilot defaults are:

| Setting | Default |
|---|---|
| Submitted file size | 15 MB per photo |
| Album photo-byte allowance | 150 MB (`MEMORIES_ALBUM_MB`) |
| Across all albums | 300 MB (`MEMORIES_TOTAL_MB`) |
| Decode dimensions after browser optimisation | 16 megapixels maximum |
| Concurrent upload requests / image processing | 2 requests / 1 image decode |
| Shared gallery page | 30 photos |

Limits are shown in the upload screen and checked transactionally. There is no automatic paid storage purchase, and increasing an app allowance does not increase Supabase’s physical storage. Supabase’s actual plan/storage limits and backups still apply. On a free database, monitor usage; database rows/images/WAL/other application data all consume space. A larger photo product may later use object storage, but this release does not require that separate service.

Rate limits protect shared links from abuse. Failed/uncertain uploads retain their request ID for safe retry, avoiding accidental duplicate saves. Only genuine, re-encoded image bytes are served; HTML/SVG uploads are not accepted as photos. Private photo responses are never service-worker cached. Use the feature online; it does not claim offline photo uploads or offline photo access.

The new tables (`memory_albums`, `memory_visitors`, `memory_photos`) live under the private `shaadi_sync` schema in PostgreSQL, with RLS and anonymous access disabled, just like the existing app. Back up the database to retain both photo bytes and album metadata. The organiser controls photo removal; this feature does not introduce an automatic deletion schedule.

## Verification

`tests/test_memories.py` exercises image validation/HEIC, sharing between named visitors, album isolation, consent/CSRF, private host recovery, moderation, rotation, persistence, quota rejection, resize and pagination. Optional PostgreSQL tests also validate actual BYTEA persistence and concurrent quota enforcement.

`tests/browser-memories.cjs` covers guest QR decoding, multi-photo upload by A, save/upload by B, ZIP download, mobile layout, partial-failure retry and host controls. It creates and cleans up its own small generated JPEG/PNG/HEIC fixtures in a temporary directory; these are not uploaded user photos. Browser checks do not verify a real physical phone camera scan, but the QR is decoded and checked against its share URL.
