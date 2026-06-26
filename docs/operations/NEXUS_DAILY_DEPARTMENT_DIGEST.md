# Nexus Daily Department Digest

The daily digest is a manual runner for the safe department feeder sequence. It is designed for a future daily morning schedule, but no scheduler is installed or started by this task.

## Command

Dry-run:

```bash
python3 scripts/automation/run_daily_department_digest.py --dry-run --limit-per-feeder 3 --no-external-ai --skip-capture
```

Bounded live project-card run:

```bash
python3 scripts/automation/run_daily_department_digest.py --no-dry-run --limit-per-feeder 3 --no-external-ai --skip-capture
```

Live mode remains bounded and creates only safe internal `task_requests` project cards and `nexus_events` proof through the feeder modules. It does not activate a scheduler.

## Included Feeders

- `opportunity_lab_research_feeder`
- `ops_improvement_research_feeder`
- `creative_studio_project_feeder`
- `design_library_project_feeder`
- `seo_marketing_project_feeder`
- `agent_jobs_process_feeder`
- `command_center_summary_feeder`
- `approvals_decision_desk_feeder`
- `events_feed_ledger_feeder`
- `integrations_status_feeder`
- `goclear_revenue_hub_feeder`
- `trading_lab_demo_research_feeder` in dry-run/status-only digest mode

## Skipped By Default

- capture queue live run
- NotebookLM live connector actions
- external AI
- publish/send/trade/deploy
- scheduler activation
- cron/launchd/systemd creation

## Reports

- `reports/runtime/daily_department_digest_latest.json`
- `reports/manual_publish/daily_department_digest_latest.md`

If live mode is explicitly used and Supabase is configured, the runner writes `nexus_events.action=daily_department_digest_completed`.

## Schedule Plan

Recommended future schedule: daily morning. Activation requires Ray approval and a separate scheduler configuration pass.
