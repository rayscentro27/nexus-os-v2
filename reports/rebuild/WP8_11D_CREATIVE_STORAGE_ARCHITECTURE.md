# WP8.11D Creative Storage Architecture

Canonical immediate flow:

`local render → deterministic object key → derivatives → copy/sync → head verification → index/ref → READY_FOR_REVIEW`

Object keys use `creative/{asset_id}/{version}/{derivative}.{ext}`. The
`CreativeStorageAdapter` exposes `put`, `head`, and `review_url`; review URLs
are logical browser paths and the UI never needs a local path. Local disk is
staging/cache for this checkpoint. A future Supabase Storage or R2 adapter may
implement the same methods after credentials, bucket policy, and private access
are independently proven.

Scope is `INTERNAL_NEXUS`; no client-sensitive or public objects are uploaded.
Approval does not publish. Missing remote access leaves the artifact available
locally and is represented as a sync/health condition rather than data loss.

