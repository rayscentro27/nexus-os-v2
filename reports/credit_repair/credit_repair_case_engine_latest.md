# Credit Repair Case Engine

- Current design preserved: `True`
- Old design restored: `False`
- Helper added: `src/lib/creditRepairCaseEngine.ts`
- Migration added: `supabase/migrations/20260710090000_credit_repair_case_engine.sql`

## Flow Added

1. Create or load active Credit Repair Case.
2. Add/review negative report items.
3. Client marks items they want challenged.
4. Client chooses the reason.
5. Nexus generates deterministic dispute letter options.
6. Client prepares a draft for GoClear specialist review.
7. Specialist review remains required.
8. Client approval remains required.
9. DocuPost send request remains approval-gated.
10. Outcomes can be recorded for next-round learning.

## Manual / Future

- Automated credit report parsing is not implemented yet; manual item entry is available.
- Secure provider integrations remain future work.
- Outcome learning is deterministic until real outcome history exists.
