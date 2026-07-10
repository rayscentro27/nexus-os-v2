# Credit Report Parser / OCR Audit

- Current branch: `feature/credit-report-parser-preview`
- Starting commit: `723a8a0`
- Current world-class client portal design preserved: `True`
- Old design restored: `False`

## Available Tools

- `package.json` has no PDF parsing or OCR dependency.
- `pdftotext` local command: unavailable.
- `tesseract` local command: unavailable.
- Python PDF/OCR packages checked: `pypdf`, `PyPDF2`, `pdfminer`, `pytesseract`; none available in the local environment.

## Implemented Preview Plan

- Added TypeScript parser types in `src/lib/creditReportParserTypes.ts`.
- Added deterministic parser engine in `src/lib/creditReportParser.ts`.
- Added local fixture CLI in `scripts/credit/parse_credit_report_fixture.py`.
- Added a narrow ReportLab text-stream fallback for the fake corpus only.
- Added admin-only parser preview language in `src/components/CreditSpecialistWorkbench.jsx`.

## Deterministic Now

- Detects broad report format guess.
- Detects bureaus by text.
- Suggests account, inquiry, personal-info, utilization, and negative-item candidates from extracted text.
- Suggests possible dispute reasons.
- Outputs draft case items only.

## Future Integration Needed

- Backend extraction worker for live uploaded files.
- Production OCR provider or local OCR service.
- Stronger PDF parser for real-world report layouts.
- Specialist UI for accepting/editing/rejecting parser suggestions against live uploaded documents.

## Specialist Gate

Parser output is never verified by the parser. It is labeled suggested extraction, needs GoClear specialist review, and does not create dispute letters or DocuPost jobs automatically.
