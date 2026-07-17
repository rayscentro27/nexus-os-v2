# Customer Admin Progress Certification

Date: 2026-07-17

## Required Journey

Certified bounded Wave 0 journey:

```text
Persona A authenticates
-> synthetic document state exists/upload contract passes
-> bounded processing completes
-> canonical account state exists
-> discrepancies and approved strategy matches are available
-> client can view progress/status
-> admin can review synthetic workflow linkage
-> follow-up synthetic upload/state is processed
-> comparison result is persisted
-> client-visible outcome remains factual and non-causal
```

## Evidence

Persona A replay:

```bash
python3 scripts/testers/replay_synthetic_credit_case.py --persona a --full
```

- Exit code: 0.
- No active duplicate jobs.
- Parser, canonical, strategy, comparison, and readiness state verified.

Authenticated browser:

```bash
npx playwright test tests/e2e/authenticated-certification.spec.ts --workers=1 --reporter=line --trace=retain-on-failure
```

- 11 passed.

Client credit workflow browser:

```bash
npx playwright test tests/e2e/client-credit-workflow-certification.spec.ts --workers=1 --reporter=line --trace=retain-on-failure
```

- 24 passed.

Guided client portal browser:

```bash
npx playwright test tests/e2e/guided-client-portal-certification.spec.ts --workers=1 --reporter=line --trace=retain-on-failure
```

- 13 passed.

## Boundaries Crossed

| Boundary | Status | Evidence |
|---|---|---|
| Browser | PASS | 48 total relevant Playwright tests passed |
| Auth | PASS | Persona A/B/C/admin login/session tests |
| Storage | PASS | Authenticated synthetic upload probe |
| Database | PASS | Synthetic replay and API assertions |
| Worker/Processing | PASS | Parser/replay/check scripts |
| RLS | PASS | Direct RLS harness and browser denial tests |
| Admin | PASS | Admin route and guided admin linkage tests |
| Client output | PASS | Non-causal checker and browser content tests |

Customer/Admin Journey Gate: PASS.
