# Nexus Department Automation Feeders

Department feeders are the safe bridge between existing data/process output and NotebookLM-style project cards. They create internal `task_requests` and `nexus_events` proof rows only. They do not activate schedulers, run capture, scrape, call external AI, publish, send, trade, deploy, modify credentials, or execute v1 workers.

## Model

Each feeder is registered in `src/config/nexusDepartmentFeeders.ts` and supported by `scripts/automation/run_department_feeder.py`.

Common fields:

`feeder_id`, `name`, `owning_department`, `owner_tab`, `purpose`, `source_type`, `script_or_process`, `manual_command`, `schedule_recommendation`, `enabled_state`, `risk_level`, `approval_required_for_schedule`, `writes_to_tables`, `writes_project_cards`, `writes_nexus_events`, `required_env`, `required_connector`, `last_run_source`, `proof_event_type`, `next_action`, and `disabled_reason`.

## Implemented Feeders

| Feeder | Department | State | Writes | Proof event |
|---|---|---|---|---|
| `source_intake_enrichment_backfill` | Source Intake | manual_only | `research_sources.metadata`, `transcript_reviews.metadata`, `nexus_events` | `project_enrichment_backfilled` |
| `source_capture_queue_worker` | Source Intake | manual_only | safe queued capture tables only when explicitly run | `source_enriched_for_project_card` |
| `opportunity_lab_research_feeder` | Opportunity Lab | manual_only | `task_requests`, `nexus_events` | `opportunity_lab_project_created` |
| `creative_studio_project_feeder` | Creative Studio | manual_only | `task_requests`, `nexus_events` | `creative_studio_project_created` |
| `design_library_project_feeder` | Design Library | manual_only | `task_requests`, `nexus_events` | `design_library_project_created` |
| `seo_marketing_project_feeder` | SEO / Marketing | manual_only | `task_requests`, `nexus_events` | `seo_marketing_project_created` |
| `agent_jobs_process_feeder` | Agent Jobs | manual_only | `task_requests`, `nexus_events` | `agent_job_project_created` |
| `command_center_summary_feeder` | Command Center | manual_only | `task_requests`, `nexus_events` | `command_center_summary_created` |
| `approvals_decision_desk_feeder` | Approvals | manual_only | `task_requests`, `nexus_events` | `approval_decision_project_created` |
| `events_feed_ledger_feeder` | Events Feed | manual_only | `task_requests`, `nexus_events` | `event_ledger_summary_created` |
| `integrations_status_feeder` | Integrations | manual_only | `task_requests`, `nexus_events` | `integration_status_project_created` |
| `trading_lab_demo_research_feeder` | Trading Lab | blocked | none in this pass | blocked |

## Commands

Dry-run one feeder:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id creative_studio_project_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live one feeder:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id creative_studio_project_feeder --no-dry-run --limit 5 --no-external-ai
```

Live runs are bounded and use duplicate prevention via:

- `task_type`
- `payload.feeder_id`
- `payload.unique_key`

## Safety Gates

- Safe feeders write internal task/project cards and proof only.
- Risky next actions remain advisory or approval-required.
- Publish, send, trade, deploy, scheduler activation, credential modification, capture, scraping, and external AI are not performed by these feeders.
- Events and Integrations feeders explicitly skip trading/Oanda items in this pass.
- Trading Lab is excluded until a separate Vibe Trading integration defines paper-only safety.

## Next Recommendation

Review the newly created department cards, then design a separate Trading Lab/Vibe Trading feeder with a paper-only broker boundary, no live execution, explicit account segregation, and proof-first dry-run reporting.
