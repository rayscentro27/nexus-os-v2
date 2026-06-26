# Nexus Data & Privacy Automation Policy

See [NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md) and
[NEXUS_HIGH_RISK_GUARDS.md](NEXUS_HIGH_RISK_GUARDS.md).

## Database / Supabase

- **Level 1:** read-only queries, internal schema reports.
- **Level 2:** schema change proposals (Ray approves before applying).
- **Level 3 (blocked):** destructive DB writes, RLS weakening, tenant isolation bypass.

Automation only appends internal cards (`task_requests`) and proof events (`nexus_events`). It
never weakens RLS, never bypasses tenant isolation, and never performs destructive writes.

## External AI on sensitive data

External AI on sensitive/private/customer/credit data is **Level 3 blocked** unless separately
approved. Research scripts run with `--no-external-ai` and operate on public/internal summaries
only. Forbidden data scopes: customer_private, credit_sensitive, funding_sensitive, auth_sensitive,
secrets.

## Secrets

Scripts never print secrets/cookies/tokens. `.env` is gitignored and must never be committed.
Guards: `secret_print`, `env_commit`, `external_ai_sensitive_data`, `client_data_exposure`,
`tenant_isolation_bypass`, `rls_weaken`, `destructive_db_write`.
