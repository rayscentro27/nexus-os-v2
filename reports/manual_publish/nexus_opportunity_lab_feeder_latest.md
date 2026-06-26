# Nexus Opportunity Lab Feeder

- generated_at: 2026-06-26
- feeder_id: `opportunity_lab_research_feeder`
- mode: bounded manual live feeder plus post-run duplicate dry-run
- no_external_ai: true
- scheduler_started: false
- capture_run: false
- publish/send/trade/deploy: false

## Implementation

The feeder scans existing `research_sources` rows that already have deterministic `metadata.project_enrichment`. It creates safe Opportunity Lab project cards as `task_requests` with `task_type=opportunity_lab_project` and writes `nexus_events` proof with `action=opportunity_lab_project_created`.

Candidate rules require public/internal-safe data, a useful recommendation, score >= 20 unless Ray review is required, and Opportunity Lab or monetization signals such as funding, credit, business, grants, marketing, sales, SEO, AI tooling, automation, creative/design, lead generation, client acquisition, GoClear, or Apex.

## Commands Verified

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --no-dry-run --limit 5 --no-external-ai
```

Post-live duplicate dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai
```

## Live Result

- scanned: 2
- eligible: 2
- created: 2
- duplicates: 0
- skipped: 0
- failed: 0
- task_requests created:
  - `2f0866c2-fe10-4719-a85d-e694842b34f4`
  - `e79a2fcf-4dda-4137-9472-769c1f776fb7`
- nexus_events proof written:
  - `423edc4a-9c96-4d49-a5ba-d7840381d95b`
  - `132d93eb-c690-4f6a-af99-6b01c0ebda22`

## Duplicate Check

A follow-up dry-run scanned the same two enriched research rows and reported:

- scanned: 2
- eligible: 0
- created: 0
- duplicates: 2
- skipped: 0
- failed: 0

## Tables And Fields Written

- `task_requests.task_type=opportunity_lab_project`
- `task_requests.status=proposed`
- `task_requests.payload.source=opportunity_lab_research_feeder`
- `task_requests.payload.project_enrichment`
- `task_requests.payload.related_research_source_id`
- `task_requests.payload.department=opportunity_lab`
- `task_requests.payload.project_type=monetization_opportunity`
- `task_requests.payload.summary`, `pros`, `cons`, `recommendation`, `proposed_schedule`, `next_action`, `score`, and `risk_triggers`
- `nexus_events.action=opportunity_lab_project_created`

## UI

Opportunity Lab reads these rows through the project adapter and can show them as department cards. Command Center counts them through the same enriched project data path.

## Next Recommendation

Review the two created Opportunity Lab cards in the UI, then implement `ops_improvement_research_feeder` with the same bounded task-request/proof-event pattern.
