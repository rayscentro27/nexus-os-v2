# Overnight Money Scheduler Proposal

- timestamp: 2026-06-27T11:29:22.584796+00:00
- status: ok
- dry_run: True
- external_action: false · money_spent: false · level_3_blocked: true

## Overnight Money Opportunity Run
- proposal_id: overnight_money_run_v1
- command: `python3 scripts/night_run/run_all_night_internal_tests.py --dry-run --cycles 8 --interval-minutes 45 --json`
- schedule: daily @ 22:00 local · 8 cycles · 45m interval
- dry_run: True · risk: medium
- approval_status: awaiting_ray_approval · activation_status: not_enabled

## Expected outputs
- reports/runtime/overnight_money_cycle_history_latest.jsonl
- reports/manual_publish/all_night_money_run_summary_latest.md
- reports/manual_publish/rolling_morning_money_agenda_latest.md
- reports/manual_publish/hermes_rolling_money_morning_brief_latest.md
- reports/manual_publish/no_external_execution_verification_latest.md

## Safety checks
- python3 scripts/safety/verify_no_external_execution.py --dry-run --json

## Blocked actions (not performed)
- install cron / launchd / systemd
- create a daemon
- publish / send / post / upload / deploy
- spend money / charge clients / activate payment links
- contact clients / activate partner links externally
- connect live Client Vault / use raw client data
- external AI on private client data / scrape / live trading
