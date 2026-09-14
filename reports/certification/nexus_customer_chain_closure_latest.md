# Customer-chain closure — 2026-09-14

`CANONICAL_TENANT_CONTRACT=tenant_memberships(tenant_id,user_id,role,client_id)`

`CONTRACT_MISMATCH=synthetic provisioner left duplicate legacy goclear memberships; replay adapter required exactly one membership`

`TENANT_CONTRACT_REPAIR=PASS_REAL`

Only duplicate `goclear` memberships for synthetic Personas A/B were removed. Their explicit `tenant-cert-persona-a/b` memberships remain. No RLS policy was weakened.

Persona A replay: `PASS_REAL` — Supabase-scoped documents 6, parser results 3, canonical accounts 3, recommendation 1, readiness history 1, no active jobs.

Persona B replay: `PASS_REAL` — Supabase-scoped documents 2, parser results 3, canonical accounts 3, recommendation 1, readiness history 1, no active jobs.

Support browser proof: Persona A and Persona B `PASS_REAL`.

Deployed gateway checks: follow-up wording → `NEXT_STEP`; cross-tenant report request → `POLICY_DENY`.

No readiness score was hard-coded or fabricated.

Remaining machine work: fresh customer-service/Clyde loop persistence, customer-bound Funding/Grants receipts, Marketing/Creative evidence, and portfolio governor reselection/start proof. TikTok, Webull, and Calendar remain external/approval-gated.
