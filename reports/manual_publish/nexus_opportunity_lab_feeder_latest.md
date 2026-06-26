# Nexus Department Automation Feeders

- generated_at: 2026-06-26T13:26:02.225425+00:00
- mode: DRY-RUN (no Supabase writes)
- feeders: 1 · no_external_ai: true
- scheduler_started: false · capture_run: false · publish/send/trade/deploy: false

## Results
- {"created": 0, "department": "opportunity_lab", "dry_run": true, "duplicates": 2, "eligible": 0, "enabled_state": "manual_only", "failed": 0, "feeder_id": "opportunity_lab_research_feeder", "limit": 3, "manual_command": "python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai", "name": "Opportunity Lab Research Feeder", "next_action": "Dry-run promotion candidates, then run bounded live creation only after reviewing candidates.", "proof_event_type": "opportunity_lab_project_created", "results": [{"source_id": "b5307732-c7c1-4d45-b230-cd78bd1efe98", "status": "duplicate", "task_request_id": "2f0866c2-fe10-4719-a85d-e694842b34f4", "title": "5 Ways to Improve Your Credit Score in 30 Days | The 700 Credit Club"}, {"source_id": "741b4d6a-1884-419b-b2b4-8f7c9a2e3a50", "status": "duplicate", "task_request_id": "e79a2fcf-4dda-4137-9472-769c1f776fb7", "title": "Hermes SEO Agent OS: How I Rank #1 on Google"}], "risk_level": "low", "scanned": 2, "skipped": 0, "status": "dry_run_reported", "target_tables": ["task_requests", "nexus_events"]}
