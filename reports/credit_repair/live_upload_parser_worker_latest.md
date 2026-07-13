# Live Upload Parser Worker Integration Report

**Date:** 2026-07-13
**Scope:** Integration test of local parser worker against live uploaded documents

## How to Run the Worker

```bash
source .venv-credit/bin/activate
python3 scripts/credit/parse_uploaded_credit_report.py --document-id <DOCUMENT_ID>
```

## What the Worker Does

1. Fetches document metadata from `client_documents` table via Supabase REST API
2. Downloads the file from Supabase Storage using the service role key
3. Extracts text using pypdf (no OCR)
4. Runs the local credit report parser (`parseCreditReportText`)
5. Saves structured results to `credit_report_parser_results` table
6. Saves local artifacts to `reports/credit_repair/uploaded_report_parser_results/`

## Output Fields

- `document_id`, `storage_path`, `source_file_name`
- `parser_version`, `extraction_mode` (local_pypdf), `extraction_success`
- `text_length`, `confidence`, `accounts`, `inquiries`, `negative_candidates`
- `structured_item_drafts`, `dispute_strategy_suggestions`
- `utilization_summary`, `bureaus_detected`, `warnings`
- `letter_preview` (empty — no auto-letters), `status` (suggested_extraction)
- `needs_specialist_review` (always true)

## Limitations

- **No OCR:** Scanned/image PDFs will fail text extraction. Manual text entry required.
- **Service role key required:** Must be set in `.env` or environment. Never exposed to frontend.
- **Local only:** Runs on admin machine, not in browser or serverless.

## Admin Workbench Integration

After running the worker, the admin workbench `CreditSpecialistWorkbench.jsx` will:
- Load the parser result via `loadParserResultForDocument()`
- Display accounts count, negative candidates, inquiries, bureaus, warnings
- Show "Confirm Items" button to create case items
- Show "Refresh" button to re-fetch latest results
- Show local worker command for reference
