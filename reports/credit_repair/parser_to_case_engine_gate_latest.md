# Parser To Case Engine Gate

Parser suggestions do not become live credit repair workflow records automatically.

## Gate Flow

1. Local/parser worker extracts text.
2. Parser returns suggested extraction with confidence and warnings.
3. Parser builds draft case-item candidates only.
4. GoClear specialist confirms, edits, or rejects selected drafts.
5. Confirmed drafts may create `credit_report_items`.
6. Client or specialist chooses a dispute reason.
7. Existing dispute option engine generates letter options.
8. Draft letters still require specialist review.
9. Client approval is required before any DocuPost/send request.

## Added Helper

- `src/lib/creditReportParserToCaseEngine.ts`

Exports:
- `buildCaseItemDraftsFromParseResult`
- `buildCaseItemDraftsFromText`
- `createConfirmedReportItemsFromDrafts`
- `createDisputeOptionsForConfirmedItem`

## Safety

- No auto-created letters.
- No auto-send.
- No service role in frontend.
- No full account numbers.
- Specialist confirmation is required before parser suggestions become case items.
