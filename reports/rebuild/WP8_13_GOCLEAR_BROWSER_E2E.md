# GoClear Browser E2E

Test: `tests/e2e/wp8-13-goclear-client-journey.spec.ts`.

Result: 2 passed against Vite with `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`, existing `.env` Supabase configuration, and existing synthetic Persona A credentials. Coverage includes authenticated login, live dashboard, Funding Readiness, inline file chooser/upload, result state, reload, mobile route, and horizontal-overflow guard.
