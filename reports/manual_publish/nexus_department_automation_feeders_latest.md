# Nexus Department Automation Feeders

- generated_at: 2026-06-26
- latest implemented feeder: `opportunity_lab_research_feeder`
- scheduler_started: false
- capture_run: false
- publish/send/trade/deploy: false
- external_ai: false

## Implemented Live Feeder

`opportunity_lab_research_feeder` is now a bounded manual live feeder. It scans existing enriched `research_sources` rows and creates safe Opportunity Lab project cards as `task_requests`.

Live write path:

- `task_requests.task_type=opportunity_lab_project`
- `task_requests.payload.project_enrichment`
- `task_requests.payload.related_research_source_id`
- `task_requests.payload.department=opportunity_lab`
- `task_requests.payload.project_type=monetization_opportunity`
- `nexus_events.action=opportunity_lab_project_created`

## Verification Snapshot

- initial dry-run: passed
- bounded live run: created 2 Opportunity Lab task cards
- proof events written: 2
- follow-up dry-run: passed and skipped both rows as duplicates
- duplicate task_requests created: 0

## Manual Commands

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --no-dry-run --limit 5 --no-external-ai
```

## Remaining Feeders

The remaining feeders are still report-only or connector-dependent:

- `ops_improvement_research_feeder`
- `creative_design_project_feeder`
- `seo_marketing_project_feeder`
- `design_library_asset_organizer`
- `agent_jobs_process_registry_feeder`

## Next Recommendation

Review the two Opportunity Lab cards in the UI, then implement the Ops & Improvements feeder using the same task-request and `nexus_events` proof pattern.
