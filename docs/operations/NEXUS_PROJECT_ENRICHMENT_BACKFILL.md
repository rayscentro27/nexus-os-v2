# Nexus Project Enrichment Backfill

`scripts/intake/backfill_project_enrichment.py` is a bounded, manual, metadata-only command for historical `research_sources` rows that predate canonical `project_enrichment`.

## Safety

- Dry-run is default.
- No YouTube capture.
- No `yt-dlp`.
- No external AI.
- No scheduler activation.
- No v1 worker access.
- No publish/send/trade/deploy.
- No duplicate `research_sources`.
- Does not change source title, URL, content, transcript text, or scoring columns.
- Does not overwrite existing `metadata.project_enrichment` unless `--force` is provided.

## Dry Run

```bash
python3 scripts/intake/backfill_project_enrichment.py --dry-run --limit 10 --no-external-ai
```

Dry-run reads candidates, computes deterministic enrichment, writes local reports only, and writes no Supabase rows/events.

## Bounded Live Run

```bash
python3 scripts/intake/backfill_project_enrichment.py --no-dry-run --limit 10 --no-external-ai
```

The live command is capped by `--limit` and hard-capped at 50 rows. For this implementation pass, do not process more than 10 live rows.

## Optional Filters

- `--source-id <uuid>`
- `--source-url <url>`
- `--force`
- `--json`
- `--report-path <path>`

## Fields Written

Existing JSON metadata only:

- `research_sources.metadata.project_enrichment`
- `research_sources.metadata.enrichment_status`
- `research_sources.metadata.enrichment_backfilled_at`
- `research_sources.metadata.enrichment_backfill_source`
- `research_sources.metadata.proof_event_id`
- Matching `transcript_reviews.metadata.*` fields when a review exists and is missing enrichment.

Live runs also write `nexus_events` with `action=project_enrichment_backfilled`.

## UI Verification

Open Source Intake. Historical source cards should show enrichment status, score label, category, destination, recommendation, pros/cons, next action, and Hermes memory summary when backfilled.

## Next Recommendation

Add an operator-only UI button later that runs a dry-run report for selected historical sources, then requires Ray confirmation before bounded live backfill.
