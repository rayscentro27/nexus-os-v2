# Credit Report Parser Preview

The parser preview is active on the preview branch only.

## What Was Added

- Normalized parser result types.
- Deterministic credit report text parser.
- Local fixture parser CLI.
- Parser-to-case-engine bridge that creates drafts and requires confirmation.
- Admin Credit Specialist preview panel.
- Client upload copy explaining that uploaded credit reports are pending GoClear review.

## Parser Output Status

- Label: `Suggested extraction`
- Verification status: `Needs GoClear specialist review`
- Verified: `False`
- Auto letter creation: `False`
- Auto DocuPost send: `False`

## Supported Suggestions

- Collection candidates
- Charge-off candidates
- Late payment candidates
- Unauthorized/unknown inquiry candidates
- High utilization candidates
- Duplicate account candidates
- Personal information variation candidates
- Mixed credit/funding bundle warning

## Limitations

- No live uploaded document parsing in the browser.
- No OCR in the current local environment.
- No fake bureau connection.
- No fake score monitoring.
- No guaranteed deletion, score increase, or funding approval language.
