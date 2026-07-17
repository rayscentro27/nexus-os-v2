# Selective Commit Plan

Generated: 2026-07-17T18:58:18Z

## Proposed Files To Stage

| Path | Why It Belongs | Verification |
| --- | --- | --- |
| `supabase/functions/accept-tester-invitation/index.ts` | Repairs acceptance and bootstraps portal baseline. | Manual deployed probe, browser 89/89, Vitest 1389/1389. |
| `supabase/functions/validate-invite-token/index.ts` | Fixes generated raw-token validation. | Browser 89/89, invite UI acceptance. |
| `src/pages/tester/TesterAcceptPage.tsx` | Stabilizes post-accept login journey. | Browser 89/89. |
| `tests/e2e/wave1-invited-tester-journey.spec.ts` | Adds real invited tester certification. | Passed independently and in 89/89 run. |
| `tests/tester_invitation.test.ts` | Updates obsolete source assertion. | Vitest 1389/1389. |
| `reports/wave-1-customer-revenue/*` | Required Wave 1 certification evidence. | Report review and secret scan. |

## Excluded Dirty Files

All dirty/untracked `data/**`, `reports/alpha/**`, `reports/runtime/**`, `reports/telegram/**`, `reports/work_orders/**`, `reports/manual_publish/**`, `tmp/**`, `test-results/**`, Telegram scripts, Alpha artifacts, and work-order draft files are excluded as unrelated/pre-existing artifacts.
