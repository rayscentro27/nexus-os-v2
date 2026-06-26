# Nexus Grouped Next Automation Layer

- generated_at: 2026-06-26
- scheduler_started: false
- cron_launchd_systemd_created: false
- capture_run: false
- yt_dlp_run: false
- external_ai_called: false
- publish_send_trade_deploy: false
- broker_api_called: false
- trade_placed: false
- credentials_or_tokens_committed: false

## Trading Import Folder

Added `reports/trading/imports/` with a README placeholder. Ray can place sanitized paper/backtest reports there, but the importer still requires an explicit file path and does not scan the folder automatically.

Dry-run:

```bash
python3 scripts/trading/import_backtest_report.py --input-file reports/trading/imports/<file>.json --dry-run --no-live-trading --json
```

## Daily Department Digest

Added `scripts/automation/run_daily_department_digest.py`.

Dry-run result: passed.

```bash
python3 scripts/automation/run_daily_department_digest.py --dry-run --limit-per-feeder 3 --no-external-ai --skip-capture
```

Reports:

- `reports/runtime/daily_department_digest_latest.json`
- `reports/manual_publish/daily_department_digest_latest.md`

The digest is manual-only now and ready for a future daily morning schedule only after Ray approves scheduler activation.

## NotebookLM Connector

Added `scripts/intake/notebooklm_connector.py`.

Dry-run status: `NotebookLM connector not configured`.

No cookies, tokens, sessions, browser profiles, browser automation, or external AI calls were used.

## Direct Source Enrichment

Added `scripts/intake/direct_source_enrichment.py`.

Dry-run result: passed for `https://example.com/test-source`.

It produced deterministic metadata-level `project_enrichment` and wrote no Supabase rows in dry-run.

## GoClear Revenue Hub

Added:

- `src/config/goclearRevenueMetrics.ts`
- `src/lib/goclearRevenueHub.ts`
- `scripts/automation/feeders/goclear_revenue_hub_feeder.py`
- GoClear / Apex department workspace project-card support

Dry-run result: passed.

Bounded live run: completed with safe internal writes only.

- created: 5
- skipped: 0
- failed: 0
- duplicates on post-live check: 5
- task type: `goclear_revenue_metric_project`
- proof event: `goclear_revenue_hub_metrics_updated`

The feeder writes estimated revenue-pipeline signal cards only. It does not call payment processors, affiliate APIs, email services, publishing services, or external AI.

## Verification

- `npm run build`: passed
- `npm run nexus:watch`: passed
- `notebooklm_connector.py` dry-run: passed
- `direct_source_enrichment.py` dry-run: passed
- `goclear_revenue_hub_feeder` dry-run: passed
- `run_daily_department_digest.py` dry-run: passed

`nexus:watch` reported scheduler not installed/started, `trade_placed=false`, and Facebook publish blocked.

## Next Recommendation

When Ray is back, review the five GoClear Revenue Hub cards and choose the first real source of truth to connect: form submissions, Stripe read-only reporting, affiliate dashboard export, or a manually reviewed CSV.
