# Nexus Department Automation Feeders

- generated_at: 2026-06-26T13:26:14.785197+00:00
- mode: DRY-RUN (no Supabase writes)
- feeders: 1 · no_external_ai: true
- scheduler_started: false · capture_run: false · publish/send/trade/deploy: false

## Results
- {"created": 0, "department": "trading_lab", "dry_run": true, "duplicates": 1, "eligible": 0, "enabled_state": "manual_only", "failed": 0, "feeder_id": "trading_lab_demo_research_feeder", "limit": 3, "live_trading_blocked": true, "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --dry-run --limit 5 --no-external-ai", "name": "Trading Lab Demo Research Feeder", "next_action": "Dry-run paper/demo research cards only; live trading remains blocked.", "paper_only": true, "proof_event_type": "trading_lab_research_project_created", "results": [{"status": "duplicate", "task_request_id": "fb08214a-1663-45b1-8e82-42c5e8a0f480", "title": "Trading Lab paper-only integration status", "unique_key": "local_report:reports/manual_publish/nexus_trading_lab_vibe_integration_latest.md"}], "risk_level": "high", "scanned": 1, "skipped": 0, "status": "dry_run_reported", "target_tables": ["task_requests", "nexus_events"]}
