# WP8.13 Durable Operator Review API

`CreativeReviewStudio` now calls `/.netlify/functions/creative-review-write` with the Supabase session bearer token. The function verifies the JWT, checks the active `admin_users` allowlist, validates asset/version/action/feedback/idempotency, and persists the review in the existing Supabase `approvals` ledger. `REQUEST_REVISION` additionally creates an existing `task_requests` row with the parent asset/version and feedback. A duplicate request returned the original receipt with `idempotent=true`; no publication fields or routes are available.

Evidence: live synthetic-admin invocation on 2026-09-02 created receipt `128f1c97-1efb-4b5f-9204-277758ed10eb`; identical replay returned the same receipt and `idempotent=true`. Browser UI wiring is covered by the Creative review component; full Netlify browser transport certification remains dependent on the local Netlify function harness.
