# Nexus Automation Schedule Plan

This is a future plan only. No cron, launchd, systemd, scheduler, capture worker, publish worker, send worker, trade worker, or deploy worker is installed or activated by the department workspace task.

The feeder registry in `src/config/nexusDepartmentFeeders.ts` prepares manual/scheduled process definitions without activating any scheduler. All feeder entries that could become scheduled have `approval_required_for_schedule=true`.

| Process | Owning tab | Script/process | Writes | Suggested schedule | Risk | Approval requirement | Manual command | Proof event | State |
|---|---|---|---|---|---|---|---|---|---|
| YouTube/research collector | Source Intake | `scripts/intake/run_existing_youtube_monitor.py` | `research_sources`, `intake_events`, `nexus_events` | 2-4 times/day after allowlist review | Medium | Required before scheduler activation | `python3 scripts/intake/run_existing_youtube_monitor.py --once --limit 1 --no-external-ai --write-events` | `source_capture_*` | Disabled/manual |
| NotebookLM source enrichment | Source Intake | Connector TBD | summaries/metadata on `research_sources` | On demand or hourly batch | Medium | Required if external connector or sensitive text | Not connected yet | `notebooklm_enrichment_*` | Disabled |
| SEO/marketing scanner | SEO / Marketing | Future scanner | `seo_opportunities`, `nexus_events` | Daily | Low/medium | Required before scheduler activation | Not connected yet | `seo_scan_*` | Disabled |
| Opportunity monetization scanner | Opportunity Lab | `scripts/intake/extract_service_opportunity.py` and future scanner | `monetization_opportunities` | Daily/manual batch | Medium | Required for client-facing promotion | `python3 scripts/intake/extract_service_opportunity.py` | `opportunity_scan_*` | Disabled/manual |
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
