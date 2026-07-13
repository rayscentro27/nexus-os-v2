# Parser Result Save Payload Fix Report

**Date:** 2026-07-13
**Scope:** Worker save payload fix — remove json.dumps() double-encoding

## What Changed

`scripts/credit/parse_uploaded_credit_report.py`:

### Before (broken)
```python
db_row = {
    "accounts": json.dumps(parse_result["accounts"]),  # JSON string
    "inquiries": json.dumps(parse_result["inquiries"]),  # JSON string
    "negative_candidates": json.dumps(parse_result["negativeItemCandidates"]),  # JSON string
    ...
}
```

### After (fixed)
```python
db_row = {
    "accounts": parse_result["accounts"],  # raw Python list → proper jsonb
    "inquiries": parse_result["inquiries"],  # raw Python list → proper jsonb
    "negative_candidates": parse_result["negativeItemCandidates"],  # raw Python list → proper jsonb
    ...
}
```

PostgREST handles JSON serialization for jsonb columns automatically. Sending raw Python objects results in proper jsonb storage.

## Verification Read-Back

After insert, the worker now reads the saved row back and verifies counts:
```
Saved row verification: accounts=26, inquiries=3, negative_candidates=26
```

If saved counts are 0 while local counts are nonzero, the worker prints a loud warning.

## Payload Summary

Added print before save:
```
Saving parser payload: accounts=26, inquiries=3, negative_candidates=26, structured_item_drafts=26, suggestions=52
```

## Safety

- No letters auto-created
- No DocuPost auto-sent
- Specialist review always required
- Client approval always required
