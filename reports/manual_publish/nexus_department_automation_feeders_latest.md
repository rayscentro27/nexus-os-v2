# Nexus Department Automation Feeders

- generated_at: 2026-06-26
- latest grouped build: Trading Lab paper-only integration
- scheduler_started: false
- capture_run: false
- publish/send/trade/deploy: false
- external_ai: false
- live_trading_blocked: true

## Implemented Live Feeders

- `opportunity_lab_research_feeder`
- `creative_studio_project_feeder`
- `design_library_project_feeder`
- `seo_marketing_project_feeder`
- `agent_jobs_process_feeder`
- `command_center_summary_feeder`
- `approvals_decision_desk_feeder`
- `events_feed_ledger_feeder`
- `integrations_status_feeder`
- `trading_lab_demo_research_feeder`

## Trading Lab Addition

Trading Lab is now manual-only, paper/demo research only. Its feeder writes `task_requests` and `nexus_events` proof with `paper_only=true` and `live_trading_blocked=true`.

It does not expose live broker execution, `auto_executor`, persistent trading loops, or schedulers.

## Latest Trading Result

- feeder: `trading_lab_demo_research_feeder`
- created: 1 paper-only research card
- duplicate dry-run after live: 1 duplicate, 0 created
- proof event: `trading_lab_research_project_created`

## Next Recommendation

Add a bounded backtest report importer that writes local JSON only and still does not call broker APIs or start trading services.
