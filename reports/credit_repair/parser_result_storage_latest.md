# Parser Result Storage Report

**Date:** 2026-07-13
**Scope:** Database schema and RLS policies for `credit_report_parser_results` table

## Table: `credit_report_parser_results`

Created via migration `20260713120000_credit_report_parser_results.sql`.

### Columns

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid (PK) | Default: gen_random_uuid() |
| `document_id` | uuid | References client_documents |
| `storage_path` | text | Supabase Storage path |
| `source_file_name` | text | Original upload filename |
| `parser_version` | text | Parser version string |
| `extraction_mode` | text | local_pypdf, local_ocr, etc. |
| `extraction_success` | boolean | Whether text was extracted |
| `text_length` | integer | Extracted text character count |
| `confidence` | text | Parser confidence level |
| `accounts` | jsonb | Array of account objects |
| `inquiries` | jsonb | Array of inquiry objects |
| `negative_candidates` | jsonb | Array of negative items |
| `structured_item_drafts` | jsonb | Draft items for case creation |
| `dispute_strategy_suggestions` | jsonb | Suggested dispute strategies |
| `utilization_summary` | jsonb | Credit utilization data |
| `bureaus_detected` | jsonb | Array of detected bureaus |
| `warnings` | jsonb | Array of parser warnings |
| `letter_preview` | text | Empty (no auto-letters) |
| `status` | text | suggested_extraction (default) |
| `needs_specialist_review` | boolean | Always true |
| `created_at` | timestamptz | Default: now() |
| `created_by` | text | Service role identifier |

### RLS Policies

- **Enable RLS** on table
- **Admin-only INSERT:** Only authenticated users with admin role can insert
- **Admin-only SELECT:** Only authenticated users with admin role can select
- **No UPDATE/DELETE policies:** Results are append-only audit trail

### Indexes

- `idx_credit_report_parser_results_document_id` on `document_id`
- `idx_credit_report_parser_results_status` on `status`

## Frontend Access

- `loadParserResultForDocument(documentId)` — loads latest result for a document
- `loadParserResultsForDocumentIds(documentIds)` — batch load for multiple documents
- Both functions use Supabase client (respects RLS)
