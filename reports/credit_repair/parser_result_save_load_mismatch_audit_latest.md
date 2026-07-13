# Parser Result Save/Load Mismatch Audit

**Date:** 2026-07-13
**Root Cause:** `json.dumps()` double-encodes jsonb columns in Supabase REST API inserts

## Summary

Ray ran the live parser worker successfully:
- 26 accounts parsed, 3 inquiries, 26 negative candidates
- DB row created: `e62cc114-aa74-4980-9205-7e1ff3695b08`

But the Admin Credit Specialist Workbench showed:
- Accounts: 0, Negative: 0, Inquiries: 0

## Root Cause

The worker (`parse_uploaded_credit_report.py`) used `json.dumps()` to convert Python lists/dicts to JSON strings before sending them in the Supabase REST API body:

```python
"accounts": json.dumps(parse_result["accounts"]),  # sends '"[{...}]"' string
```

PostgREST received a JSON string value for a jsonb column, stored it as a JSON-encoded string instead of a proper jsonb array. When the frontend queried with `select('*')`, it received the string `"[{...}]"` instead of the array `[{...}]`. `Array.isArray()` returned false, so all counts showed 0.

## Local Artifact Counts

From `reports/credit_repair/live_upload_parser_results/a2b1e51d-6ca8-4445-9d18-c1873d8baf34_1783727061077/parse_result.json`:
- Accounts: 26
- Inquiries: 3
- Negative candidates: 26
- Bureaus detected: experian, equifax, transunion
- Personal info variations: 2
- Warnings: 1

## Database Insert Payload (Before Fix)

| Field | Sent as | Stored as | Frontend reads |
|-------|---------|-----------|----------------|
| accounts | `json.dumps([...])` | `"[{...}]"` string | `Array.isArray()` → false → 0 |
| inquiries | `json.dumps([...])` | `"[{...}]"` string | `Array.isArray()` → false → 0 |
| negative_candidates | `json.dumps([...])` | `"[{...}]"` string | `Array.isArray()` → false → 0 |

## Fix

1. Worker: Remove `json.dumps()` for all jsonb columns — send raw Python objects
2. Worker: Add verification read-back after insert
3. Frontend: Add `parseJsonbField()` fallback to handle any remaining double-encoded data
4. Frontend: Mismatch detection when textLength > 0 but accounts = 0

## How to Retest

```bash
source .venv-credit/bin/activate
python3 scripts/credit/parse_uploaded_credit_report.py --document-id a2b1e51d-6ca8-4445-9d18-c1873d8baf34_1783727061077 --out reports/credit_repair/live_upload_parser_results
```

Expected output:
- `Saving parser payload: accounts=26, inquiries=3, negative_candidates=26`
- `Saved row verification: accounts=26, inquiries=3, negative_candidates=26`

Then refresh parser results in the Admin Workbench.

## Old Zero Result

The existing DB row (e62cc114) has double-encoded data. The worker's upsert will overwrite it with correct data on re-run.
