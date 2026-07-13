# Admin Parser Result Review Report

**Date:** 2026-07-13
**Scope:** Admin workbench UI for reviewing parser results and confirming items

## Flow

1. Admin opens Credit Specialist Workbench
2. Selects a pending credit report review
3. Clicks "Run Parser Preview" → parser panel opens
4. If parser worker has been run for this document, results load automatically
5. If no results exist, shows local worker command and refresh button
6. Admin sees: accounts count, negative candidates, inquiries, bureaus, warnings
7. Admin clicks "Confirm Items" to create case items from parser drafts
8. Admin can click "Refresh" to re-fetch latest results

## UI Elements

### Parser Panel (when results exist)
- **Stats grid:** Accounts / Negative / Inquiries counts
- **Extraction info:** Mode, confidence, detected bureaus
- **Warnings:** Any parser warnings displayed
- **Suggested extraction notice:** "Needs GoClear specialist review. Not verified yet."
- **Item count:** Number of suggested items ready for review
- **Action buttons:** Refresh, Confirm Items

### Parser Panel (when no results)
- **Worker command:** Shows exact command to run locally
- **Refresh button:** Re-fetches from DB
- **Note:** "No parser result found for this document."

### Confirm Items Flow
1. Click "Confirm Items" → creates case (if none exists)
2. Calls `confirmParserItemAsCaseItem()` for each parser draft
3. Each item marked as `parser_confirmed` source
4. Dispute strategy must be selected by specialist or client
5. No letters created automatically
6. No DocuPost sent

## Safety rails

- Confirm button disabled when no parser items exist
- All results clearly marked as suggested extraction
- No auto-letter creation
- No auto-DocuPost sending
- No bureau credential collection
- No SSN/full DOB/full EIN/full account number collection
- Specialist or client must approve dispute strategy
