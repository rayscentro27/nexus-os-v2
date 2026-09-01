# WP8.11E Supabase Creative Storage

Existing Supabase configuration was discovered in `.env` and credentials were not printed. The existing project was reachable over TLS with both anon and service paths. A dedicated `creative-assets` bucket was created private (`public=false`) using the existing service credential; no R2 or paid infrastructure was added.

Real WP8.11B artifacts were synchronized: 16 objects across five indexed assets, including image masters/derivatives, landing screenshots, video master/review/poster/thumb. Each upload was followed by authenticated existence verification. Signed review URLs returned real bytes and correct content types for the video poster (`image/jpeg`, 97,130 bytes), review proxy (`video/mp4`, 80,528 bytes), and thumbnail (`image/jpeg`, 97,130 bytes).

The local store remains staging/cache and the index now carries provider-neutral remote review references. Browser use of a private remote object requires a valid signed/authenticated session; static URLs are time-limited and are not treated as permanent public authority. Fallback remains local staging with `REMOTE_SYNC_PENDING` semantics.
