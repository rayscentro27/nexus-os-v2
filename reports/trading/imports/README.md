# Trading Lab Import Drop Folder

Ray may place explicit paper/backtest report files here for manual Trading Lab import.

Allowed:

- paper/demo backtest JSON, CSV, Markdown, or text reports
- strategy research summaries with no broker credentials
- sanitized paper/demo signal summaries

Blocked:

- broker credentials, tokens, cookies, private keys, or session files
- live order logs that expose account-sensitive data
- funded account statements or customer/private financial data
- anything intended to trigger live trading

The importer does not scan this folder automatically. Run it with an explicit file path:

```bash
python3 scripts/trading/import_backtest_report.py --input-file reports/trading/imports/<file>.json --dry-run --no-live-trading --json
```
