# Nexus Project Enrichment Model

Project enrichment is a deterministic, schema-light payload stored in existing JSON fields. It gives department cards and Hermes consistent summaries, scores, recommendations, pros/cons, next actions, and schedule guidance without external AI or scheduler activation.

## Canonical Payload

Stored as `project_enrichment`:

- `enrichment_status`: `metadata_saved`, `pending_transcript`, `pending_notebooklm`, `enriched`, `scored`, `needs_review`, `failed`
- `summary`
- `score`
- `score_label`
- `category`
- `destination`
- `pros`
- `cons`
- `recommendation`
- `proposed_schedule`
- `next_action`
- `confidence`
- `risk_triggers`
- `approval_required`
- `hermes_memory_summary`
- `source_summary`
- `enrichment_source`: `deterministic`, `transcript_capture`, `notebooklm`, `manual`, `fallback`
- `enriched_at`
- `reviewed_at`
- `proof_event_id`

## Storage

- `research_sources.metadata.project_enrichment`: primary source card enrichment.
- `transcript_reviews.metadata.project_enrichment`: richer transcript-derived enrichment when review data exists.
- `task_requests.payload.project_enrichment`: worker/request result context.
- `nexus_events.payload.project_enrichment`: proof snapshot for `source_enriched_for_project_card`.

No schema migration is required. Existing columns such as `snippet`, `why_it_matters`, `confidence`, transcript review score fields, and rating metadata are still used.

## Deterministic Helper

`scripts/intake/nexus_enrichment.py` builds the payload from saved source metadata, transcript review fields, task payload, and rating metadata. It uses templates and rules only. It does not call external AI.

Rules include:

- Missing transcript produces: "Saved metadata is available. Transcript/NotebookLM enrichment is pending."
- Low scores add a low-score risk/cons note.
- `credit_funding_readiness` routes to GoClear/Apex funding readiness.
- `ai_tooling`, `system_improvement`, and `operations` route to Ops & Improvements.
- Opportunity destinations produce monetization-review guidance.
- Risk triggers or approval-required fields recommend Ray review.

## Project Card Read Order

`src/lib/nexusProjects.ts` reads enrichment in this order:

1. `transcript_reviews.metadata.project_enrichment`
2. `research_sources.metadata.project_enrichment`
3. `task_requests.payload.project_enrichment`
4. deterministic fallback from available columns/metadata

Hermes reads the selected project's `hermes_memory_summary`, summary, recommendation, pros/cons, risk, next action, and proposed schedule.

## Remaining Work

- NotebookLM connector enrichment is still planned, not connected.
- Existing historical rows may need a manual backfill if richer cards are desired without new captures.
- Future dedicated Hermes memory table migration can replace storing `hermes_memory_summary` in metadata.
