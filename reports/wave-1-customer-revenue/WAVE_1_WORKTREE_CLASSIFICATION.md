# Wave 1 Worktree Classification

Generated: 2026-07-17T18:58:18Z

## Wave 1 Candidate Files

| Path | Classification | Reason |
| --- | --- | --- |
| `supabase/functions/accept-tester-invitation/index.ts` | Wave 1 implementation | Repairs invitation acceptance auth-admin usage and bootstraps client membership/profile/readiness/tasks. |
| `supabase/functions/validate-invite-token/index.ts` | Wave 1 implementation | Repairs raw-token/hash validation ambiguity for generated 64-hex invitations. |
| `src/pages/tester/TesterAcceptPage.tsx` | Wave 1 implementation | Stabilizes post-accept path through explicit client login. |
| `tests/e2e/wave1-invited-tester-journey.spec.ts` | Wave 1 certification | Real browser invitation redemption and portal/RLS certification. |
| `tests/tester_invitation.test.ts` | Wave 1 test update | Replaces obsolete `inviteUserByEmail` source expectation with current service-role auth/bootstrap contract. |
| `reports/wave-1-customer-revenue/*` | Wave 1 documentation | Required certification reports. |

## Protected Exclusions

Pre-existing dirty/untracked paths under `data/**`, `reports/alpha/**`, `reports/runtime/**`, `reports/telegram/**`, `reports/work_orders/**`, `reports/manual_publish/**`, `tmp/**`, Telegram scripts, Alpha artifacts, work-order drafts, and `test-results/**` were not modified for Wave 1 and must remain unstaged unless separately reviewed.
