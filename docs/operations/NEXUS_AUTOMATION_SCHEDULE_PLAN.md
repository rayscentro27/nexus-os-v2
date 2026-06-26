# Nexus Automation Schedule Plan

This is a future plan only. No cron, launchd, systemd, scheduler, capture worker, publish worker, send worker, trade worker, or deploy worker is installed or activated by the department workspace task.

The feeder registry in `src/config/nexusDepartmentFeeders.ts` prepares manual/scheduled process definitions without activating any scheduler. All feeder entries that could become scheduled have `approval_required_for_schedule=true`.

| Process | Owning tab | Script/process | Writes | Suggested schedule | Risk | Approval requirement | Manual command | Proof event | State |
|---|---|---|---|---|---|---|---|---|---|
| YouTube/research collector | Source Intake | `scripts/intake/run_existing_youtube_monitor.py` | `research_sources`, `intake_events`, `nexus_events` | 2-4 times/day after allowlist review | Medium | Required before scheduler activation | `python3 scripts/intake/run_existing_youtube_monitor.py --once --limit 1 --no-external-ai --write-events` | `source_capture_*` | Disabled/manual |
| NotebookLM source enrichment | Source Intake | Connector TBD | summaries/metadata on `research_sources` | On demand or hourly batch | Medium | Required if external connector or sensitive text | Not connected yet | `notebooklm_enrichment_*` | Disabled |
| SEO/marketing scanner | SEO / Marketing | Future scanner | `seo_opportunities`, `nexus_events` | Daily | Low/medium | Required before scheduler activation | Not connected yet | `seo_scan_*` | Disabled |
| Opportunity monetization scanner | Opportunity Lab | `scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder` | `task_requests`, `nexus_events` | Manual now; future daily after approval | Low/medium | Required before scheduler activation and for any client-facing promotion | `python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai` | `opportunity_lab_project_created` | Manual only |
| Daily department digest | Command Center | `scripts/automation/run_daily_department_digest.py` | local reports, optional safe feeder cards/proof | Future daily morning after approval | Medium | Required before scheduler activation | `python3 scripts/automation/run_daily_department_digest.py --dry-run --limit-per-feeder 3 --no-external-ai --skip-capture` | `daily_department_digest_completed` | Manual only / ready for schedule |
| GoClear Revenue Hub feeder | GoClear / Apex | `scripts/automation/run_department_feeder.py --feeder-id goclear_revenue_hub_feeder` | `task_requests`, `nexus_events` | Future daily with digest after approval | Low | Required before connector-backed revenue sync | `python3 scripts/automation/run_department_feeder.py --feeder-id goclear_revenue_hub_feeder --dry-run --limit 5 --no-external-ai` | `goclear_revenue_hub_metrics_updated` | Manual only |
| Creative idea/project generator | Creative Studio | `scripts/creative/*` | creative tables, approvals when needed | Manual or weekly | Medium | Publish/send requires approval | Existing creative scripts manually | `creative_job_*` | Manual |
| Design asset organizer | Design Library | `scripts/design/*` | design tables | Weekly/manual | Low | Approval for public/client-facing use | Existing design scripts manually | `design_refresh_*` | Manual |
| Ops self-audit | Ops & Improvements | `scripts/run_nexus_continuous_operations.py --mode manual` | health/events/improvements | Manual now; future daily | Medium | Required before scheduler activation | `npm run nexus:watch` | `watch_report_*` | Manual |
| Process Registry refresh | Agent Jobs/Ops | Future process registry script | process registry rows/events | Daily/manual | Medium | Required before scheduler activation | Not connected yet | `process_registry_refresh` | Disabled |
| System Health refresh | System Health/Command Center | `npm run nexus:watch` | `system_health`, reports/events | Manual now | Low | Scheduler activation requires approval | `npm run nexus:watch` | `system_health_refresh` | Manual |
| Hermes memory consolidation | Command Center | Future memory worker | `nexus_lessons`, memory metadata | Weekly/manual | Medium | Required if external AI or sensitive data | Not connected yet | `hermes_memory_consolidation` | Disabled |

## Manual Feeder Runner

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --dry-run --limit 5 --no-external-ai
```

This reports target departments, write tables, and proof event types. It does not install or start cron, launchd, systemd, or any persistent process.

Opportunity Lab bounded live command, only after reviewing dry-run candidates:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --no-dry-run --limit 5 --no-external-ai
```

This command creates internal `task_requests` project cards and `nexus_events` proof only. It does not publish, send, trade, deploy, scrape, capture, or activate scheduling.

## Non-Trading Department Feeders

The remaining non-trading feeders are manual-only and bounded:

| Feeder | Department | Manual dry-run | Proof |
|---|---|---|---|
| `creative_studio_project_feeder` | Creative Studio | `python3 scripts/automation/run_department_feeder.py --feeder-id creative_studio_project_feeder --dry-run --limit 5 --no-external-ai` | `creative_studio_project_created` |
| `design_library_project_feeder` | Design Library | `python3 scripts/automation/run_department_feeder.py --feeder-id design_library_project_feeder --dry-run --limit 5 --no-external-ai` | `design_library_project_created` |
| `seo_marketing_project_feeder` | SEO / Marketing | `python3 scripts/automation/run_department_feeder.py --feeder-id seo_marketing_project_feeder --dry-run --limit 5 --no-external-ai` | `seo_marketing_project_created` |
| `agent_jobs_process_feeder` | Agent Jobs | `python3 scripts/automation/run_department_feeder.py --feeder-id agent_jobs_process_feeder --dry-run --limit 5 --no-external-ai` | `agent_job_project_created` |
| `command_center_summary_feeder` | Command Center | `python3 scripts/automation/run_department_feeder.py --feeder-id command_center_summary_feeder --dry-run --limit 5 --no-external-ai` | `command_center_summary_created` |
| `approvals_decision_desk_feeder` | Approvals | `python3 scripts/automation/run_department_feeder.py --feeder-id approvals_decision_desk_feeder --dry-run --limit 5 --no-external-ai` | `approval_decision_project_created` |
| `events_feed_ledger_feeder` | Events Feed | `python3 scripts/automation/run_department_feeder.py --feeder-id events_feed_ledger_feeder --dry-run --limit 5 --no-external-ai` | `event_ledger_summary_created` |
| `integrations_status_feeder` | Integrations | `python3 scripts/automation/run_department_feeder.py --feeder-id integrations_status_feeder --dry-run --limit 5 --no-external-ai` | `integration_status_project_created` |

No scheduler is activated for these feeders. Trading Lab is manual-only paper research and requires a separate approval before any future paper/demo loop. Live trading remains blocked.

## Trading Lab / Vibe Trading

| Process | Owning tab | Script/process | Writes | Suggested schedule | Risk | Approval requirement | Manual command | Proof event | State |
|---|---|---|---|---|---|---|---|---|---|
| Vibe Trading status adapter | Trading Lab | `scripts/trading/vibe_trading_adapter.py` | local report only | Manual only | High | Required for anything beyond status/backtest report | `python3 scripts/trading/vibe_trading_adapter.py --dry-run --mode status --no-live-trading` | local report | Manual only |
| Trading backtest report importer | Trading Lab | `scripts/trading/import_backtest_report.py` | local report, optional `task_requests`, `nexus_events` | Manual only | High | Required for anything beyond explicit paper/backtest report import | `python3 scripts/trading/import_backtest_report.py --sample --dry-run --no-live-trading --json` | `trading_backtest_report_imported` | Manual only |
| Trading Lab paper research feeder | Trading Lab | `scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder` | `task_requests`, `nexus_events` | Manual only | High | Required before any demo loop/scheduler/broker connection | `python3 scripts/automation/run_department_feeder.py --feeder-id trading_lab_demo_research_feeder --dry-run --limit 5 --no-external-ai` | `trading_lab_research_project_created` | Manual only |

Blocked commands: `auto_executor.py`, `nexus_trading_engine.py`, `tournament_service.py`, webhook/manual signal endpoints, broker order paths, and scheduler activation.
