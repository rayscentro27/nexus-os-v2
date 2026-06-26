# Nexus Content Test Tracker

`scripts/research/content_test_tracker.py` imports manual content test CSV files.

Command:

```bash
python3 scripts/research/content_test_tracker.py --input-file reports/content/test_imports/sample_content_tests.csv --dry-run --json
```

The safe import folder is `reports/content/test_imports/`.

Fields: content title, channel, target keyword, offer, affiliate program, published URL, status, impressions, clicks, leads, conversions, revenue, estimated value, and next action.

No live analytics API is connected in this pass.
