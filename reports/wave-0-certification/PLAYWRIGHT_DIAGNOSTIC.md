# Playwright Diagnostic

Date: 2026-07-17

## Configuration

File: `playwright.config.ts`

- Test directory: `tests/e2e`
- Timeout: 60 seconds.
- Base URL: `E2E_BASE_URL` or `http://127.0.0.1:4173`.
- Web server command when `E2E_BASE_URL` is not set:

```bash
VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true npm run build && npm run preview -- --host 127.0.0.1 --port 4173
```

Observation:

- Playwright does not automatically read `.env.e2e.local`; certification commands loaded `.env` and `.env.e2e.local` silently through shell before invoking Playwright.
- The webServer build step completes but adds roughly one minute per suite.

## Persona A Smallest Test

Command:

```bash
npx playwright test tests/e2e/authenticated-certification.spec.ts -g "Persona A: client login succeeds" --workers=1 --reporter=line --trace=retain-on-failure
```

Result:

- 1 passed.
- Exit code: 0.
- Status: PASS.

## Synthetic Admin Smallest Test

Command:

```bash
npx playwright test tests/e2e/authenticated-certification.spec.ts -g "Admin: can access credit specialist route" --workers=1 --reporter=line --trace=retain-on-failure
```

Result:

- 1 passed.
- Exit code: 0.
- Status: PASS.

## Full Authenticated Certification

Command:

```bash
npx playwright test tests/e2e/authenticated-certification.spec.ts --workers=1 --reporter=line --trace=retain-on-failure
```

Result:

- 11 passed.
- Exit code: 0.
- Status: PASS.

Coverage:

- Persona A login/session.
- Persona B login/session.
- Persona C login/session.
- Client denial from admin routes.
- Synthetic admin login/session.
- Admin route access.
- Admin denial from client portal.
- Browser-level RLS denial probes.

## Client Credit Workflow Certification

Command:

```bash
npx playwright test tests/e2e/client-credit-workflow-certification.spec.ts --workers=1 --reporter=line --trace=retain-on-failure
```

Result:

- 24 passed.
- Exit code: 0.
- Status: PASS.

Coverage:

- Strategy cards.
- Strategy decisions.
- Decision persistence.
- Document vault visibility.
- No public permanent storage URL in page content.
- Cross-client denial.
- Safe draft language.
- Persona B uncertainty and specialist review.
- Persona C purchased-debt path.
- Progress timeline.

## Guided Client Portal Certification

Command:

```bash
npx playwright test tests/e2e/guided-client-portal-certification.spec.ts --workers=1 --reporter=line --trace=retain-on-failure
```

Result:

- 13 passed.
- Exit code: 0.
- Status: PASS.

Coverage:

- Persona A dashboard, credit, documents, request review.
- Persona B exception state.
- Persona C funding-readiness state.
- Client/tester isolation.
- Synthetic admin linkage to Ray Review draft.
- Desktop/laptop/mobile no horizontal overflow.

## Browser Gate

Persona A Browser: PASS.
Admin Browser: PASS.
