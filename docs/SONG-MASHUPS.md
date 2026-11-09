# Song mashup uploads

Guests and authorised co-organisers can attach an audio mashup while adding or editing a song under Celebrations. The Spotify song link remains optional and works alongside an uploaded file. Guest requests show an Edit my song / mashup action. Co-organisers need the `songs` permission granted by the owner; demo co-organisers already have it.

Supported formats are MP3, WAV, M4A and OGG (Vorbis/Opus), up to 20 MB and 30 minutes per file. MP3 has the broadest phone compatibility; M4A and OGG codec support depends on the browser. The server validates file contents with Mutagen rather than trusting the filename or browser MIME type. Uploads require confirmation that the audio can be shared with the wedding organisers.

Song cards show playback controls and a download link. Uploading a replacement replaces the previous file only after validation and quota checks succeed. Removing the audio keeps the song and its Spotify link. If audio upload fails after song metadata is saved, the form keeps the song ID for retry so it does not create duplicate song entries. Original uploaded audio bytes and embedded metadata are retained; the app does not transcode files or autoplay them.

Files use a private database table, with BLOB storage in SQLite and BYTEA in PostgreSQL. The additive table and index are created automatically on deployment. PostgreSQL row-level security and existing private-schema restrictions apply. SQLite backups include the audio, and PostgreSQL managed backups/pg_dump should include the `shaadi_sync` schema. Removing a song or its demo workspace cascades removal of its file. File sizes and names appear in song metadata; audio bytes are never attached to state responses.

Guests can upload, play, download, replace and remove audio only for their own song requests. Owners and co-organisers with song permissions can manage the wedding's song audio. Other weddings and unrelated staff roles cannot access it. Mutations require a current authenticated session and CSRF token; playback and downloads require authentication, bypass service-worker caching, return `private, no-store`, and support HTTP byte ranges for seeking.

Default byte allowances are 75 MB per wedding and 150 MB across the app. Change `SONG_AUDIO_EVENT_MB` and `SONG_AUDIO_TOTAL_MB` in hosting settings if database capacity permits. Storage is separate from the Memories photo allowance; both consume database capacity. Uploads are limited to 30 attempts per account per hour and share the existing two-upload concurrency bound with photo uploads.

Render's existing build command installs `mutagen==1.47.0` from requirements.txt. No external audio account, Spotify login, Supabase bucket, or ffmpeg installation is needed on the deployed server. Automated format tests can use ffmpeg only to generate fixtures; production validation uses Mutagen and playback uses the visitor's browser.
