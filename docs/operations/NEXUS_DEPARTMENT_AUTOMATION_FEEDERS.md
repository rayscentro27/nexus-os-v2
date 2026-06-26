# Nexus Department Automation Feeders

Department feeders are the safe bridge between manual/scheduled processes and NotebookLM-style project cards. This layer defines what can feed each department, what it writes, and what proof event it emits. It does not activate persistent scheduling.

## Model

Each feeder is registered in `src/config/nexusDepartmentFeeders.ts` with:

`feeder_id`, `name`, `owning_department`, `owner_tab`, `purpose`, `source_type`, `script_or_process`, `manual_command`, `schedule_recommendation`, `enabled_state`, `risk_level`, `approval_required_for_schedule`, `writes_to_tables`, `writes_project_cards`, `writes_nexus_events`, `required_env`, `required_connector`, `last_run_source`, `proof_event_type`, `next_action`, and `disabled_reason`.

Enabled states:

- `manual_only`
- `ready_for_schedule`
- `disabled`
- `blocked`
- `needs_connector`

## Feeders

| Feeder | Department | State | Manual command | Writes | Proof |
|---|---|---|---|---|---|
| `source_intake_enrichment_backfill` | Source Intake | manual_only | `python3 scripts/intake/backfill_project_enrichment.py --dry-run --limit 10 --no-external-ai` | `research_sources.metadata`, `transcript_reviews.metadata`, `nexus_events` | `project_enrichment_backfilled` |
| `source_capture_queue_worker` | Source Intake | manual_only | `python3 scripts/intake/run_capture_queue_worker.py --once --limit 1 --dry-run --no-external-ai` | `task_requests`, `research_sources`, `intake_events`, `transcript_reviews`, `nexus_events` | `source_enriched_for_project_card` |
| `ops_improvement_research_feeder` | Ops & Improvements | manual_only | `python3 scripts/automation/run_department_feeder.py --feeder-id ops_improvement_research_feeder --dry-run --limit 5 --no-external-ai` | future `task_requests`, `nexus_events` | `department_feeder_ops_improvement_reported` |
| `opportunity_lab_research_feeder` | Opportunity Lab | manual_only | `python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai` | future `task_requests`, `nexus_events` | `department_feeder_opportunity_reported` |
| `creative_design_project_feeder` | Creative Studio | manual_only | `python3 scripts/automation/run_department_feeder.py --feeder-id creative_design_project_feeder --dry-run --limit 5 --no-external-ai` | future `task_requests`, `creative_assets.metadata`, `nexus_events` | `department_feeder_creative_design_reported` |
| `seo_marketing_project_feeder` | SEO / Marketing | needs_connector | `python3 scripts/automation/run_department_feeder.py --feeder-id seo_marketing_project_feeder --dry-run --limit 5 --no-external-ai` | future `task_requests`, `seo_opportunities`, `nexus_events` | `department_feeder_seo_reported` |
| `design_library_asset_organizer` | Design Library | manual_only | `python3 scripts/automation/run_department_feeder.py --feeder-id design_library_asset_organizer --dry-run --limit 5 --no-external-ai` | future `task_requests`, `nexus_events` | `department_feeder_design_reported` |
| `agent_jobs_process_registry_feeder` | Agent Jobs | manual_only | `python3 scripts/automation/run_department_feeder.py --feeder-id agent_jobs_process_registry_feeder --dry-run --limit 5 --no-external-ai` | future `task_requests`, `nexus_events` | `department_feeder_agent_jobs_reported` |
| `command_center_executive_summary_feeder` | Command Center | manual_only | `python3 scripts/automation/run_department_feeder.py --department command_center --dry-run --limit 5 --no-external-ai` | `nexus_events` if live status report is explicitly run | `department_feeder_command_center_reported` |
| `approvals_decision_desk_feeder` | Approvals | manual_only | Open Approvals tab | `approvals`, `nexus_events` | `approval_required` |
| `events_feed_ledger_feeder` | Events Feed | manual_only | Open Events Feed tab | `nexus_events` | `nexus_event` |
| `integrations_connection_status_feeder` | Integrations | manual_only | `npm run nexus:watch` | `system_health`, `nexus_events` | `integration_status_reported` |
| `trading_lab_demo_research_feeder` | Trading Lab | blocked | dry-run only | future `task_requests`, `nexus_events` | `department_feeder_trading_demo_reported` |

## Runner

`scripts/automation/run_department_feeder.py` is a manual runner skeleton. Dry-run is default:

```bash
python3 scripts/automation/run_department_feeder.py --dry-run --limit 5 --no-external-ai
```

Specific feeder dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id source_intake_enrichment_backfill --dry-run --limit 5 --no-external-ai
```

The runner reports what a feeder would target, which tables it would write, and which proof event it would emit. It does not run capture, `yt-dlp`, external AI, publishing, sending, trading, deployment, broad scraping, v1 workers, or scheduler activation.

## UI

Department rooms show feeder cards with state, source type, proof event, and next action. Command Center shows feeder counts for manual-only, ready-for-schedule, blocked, and needs-connector states.

## Scheduler Policy

All feeders requiring schedule activation have `approval_required_for_schedule=true`. No cron, launchd, systemd, or persistent scheduler is created by this layer.

## Next Recommendation

Implement the first live non-capture feeder as a bounded `opportunity_lab_research_feeder` that creates task_requests from already-enriched `research_sources` with Opportunity Lab/GoClear destinations, after Ray reviews the dry-run report.
