# WP8.12 Operator Authentication

The new `/operator` route uses the existing `AdminGuard` followed by `AuthGate`; no bypass or alternate authority was introduced. The existing idempotent synthetic certification workflow provisioned/repaired `nexus-cert-admin` and four test personas using the existing Supabase service path. Credentials remain in ignored `.env.e2e.local` and are not printed or committed.

`OPERATOR_TEST_AUTH_PATH=PASS`; authenticated Playwright login and session access passed.
