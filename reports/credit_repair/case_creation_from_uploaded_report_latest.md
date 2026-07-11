# Case Creation From Uploaded Report

## Helper Added

- `src/lib/creditRepairCaseEngine.ts`
- Export: `getOrCreateCreditRepairCaseForDocument`

## Behavior

- Finds an existing active `credit_repair_cases` row for the client.
- If none exists, creates a new case with status `report_uploaded`.
- Stores source document context in `case_goal` because the current schema does not include a dedicated source document column.
- Returns a safe result for UI feedback.

## Safety

- Does not create dispute letters.
- Does not create DocuPost/send requests.
- Does not bypass specialist review.
- Does not bypass client approval.
