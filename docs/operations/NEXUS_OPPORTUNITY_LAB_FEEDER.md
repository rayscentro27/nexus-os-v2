# Nexus Opportunity Lab Feeder

`opportunity_lab_research_feeder` is a bounded manual feeder that turns already-enriched public research rows into Opportunity Lab project cards. It does not run capture, `yt-dlp`, scraping, external AI, publishing, sending, trading, deployment, v1 workers, or schedulers.

## Inputs

- `research_sources`
- `research_sources.metadata.project_enrichment`
- optional metadata fields such as tags, category, destination, sensitivity, and status

The feeder only uses stored metadata and deterministic enrichment. It does not fetch source content.

## Candidate Rules

Include rows when they are public/internal safe and likely useful for monetization or business review:

- destination includes Opportunity Lab
- category, tags, title, summary, or recommendation includes funding, credit, monetization, business, grants, marketing, sales, SEO, AI tooling, automation, creative, design, lead generation, client acquisition, GoClear, Apex, affiliate, or opportunity
- score is at least 20, unless the row already requires Ray review
- project enrichment includes a recommendation

Exclude rows when they contain sensitive/private/customer data, high-risk triggers, rejected/parked status, or an existing `task_requests` row from this feeder for the same source.

## Duplicate Prevention

Before creating a card, the feeder checks `task_requests` for:

- `task_type=opportunity_lab_project`
- `payload.feeder_id=opportunity_lab_research_feeder`
- `payload.related_research_source_id=<research_sources.id>`

Matching rows are skipped as duplicates and reported in dry-run output.

## Commands

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id opportunity_lab_research_feeder --no-dry-run --limit 5 --no-external-ai
```

Live runs are capped at 10 by the feeder, and the recommended command uses a limit of 5.

## Writes

Live runs create internal project-card rows in `task_requests`:

- `task_type=opportunity_lab_project`
- `status=proposed` or `needs_review`
- `approval_required=false` unless risk triggers require Ray review
- `payload.source=opportunity_lab_research_feeder`
- `payload.project_enrichment`
- `payload.related_research_source_id`
- `payload.source_url`
- `payload.department=opportunity_lab`
- `payload.project_type=monetization_opportunity`
- `payload.summary`, `pros`, `cons`, `recommendation`, `proposed_schedule`, `next_action`, `score`, and `risk_triggers`

Each created card writes a `nexus_events` proof row with `action=opportunity_lab_project_created`, the feeder id, research source id, task request id, score, and recommendation summary.

## UI

Opportunity Lab reads these task requests through `src/lib/nexusProjects.ts`. Cards show source, score, summary, pros, cons, recommendation, proposed schedule, next action, and review status. Command Center counts them through the same project adapter.

## Verification Snapshot

On the bounded live run, the feeder created two Opportunity Lab task cards and two `nexus_events` proof rows. A follow-up dry-run scanned the same two rows and skipped both as duplicates.

## Next Recommendation

Review the two created Opportunity Lab cards in the UI, then implement a bounded `ops_improvement_research_feeder` using the same task-request/proof-event pattern.
