# Nexus Research And Automation Architecture

## A. Instant Research Mode

Ray's one-off research should feel immediate. When Ray pastes a YouTube URL, public link, or public text, the UI saves a `research_sources` row immediately and shows a visible source/project card. Hermes can review the saved title, URL, snippet, metadata, destination, and pending status right away.

Instant mode behavior:

- Save source immediately to Supabase.
- Show the card immediately in Source Intake.
- Create a preliminary score only when deterministic metadata is available.
- Mark enrichment as pending without making the UI queue-first.
- Allow Hermes to say: "I can review the saved metadata now. Summary/enrichment is pending."
- File safe enrichment/capture work through existing `task_requests` and policy helpers.
- Store deterministic card enrichment in `research_sources.metadata.project_enrichment`, then prefer richer `transcript_reviews.metadata.project_enrichment` when available.
- Do not call external AI on sensitive/private/customer text.
- Do not run broad scraping or browser capture.

Metadata-first direct enrichment is available for one explicit public source:

```bash
python3 scripts/intake/direct_source_enrichment.py --source-url "https://example.com/test-source" --title "Safe Test Source" --dry-run --no-external-ai --json
```

## B. Scheduled Automation Mode

Scheduled automation is for background intelligence, not Ray's one-off intake. These processes can collect, enrich, score, and feed department boards after deliberate activation.

Planned feeds:

- YouTube/research monitoring feeds Source Intake.
- NotebookLM source enrichment feeds Source Intake summaries if a connector is available.
- SEO checks feed Growth Department.
- Opportunity scans feed Opportunity Lab.
- Creative/design generation feeds Creative Studio and Design Library.
- System improvement research feeds Ops & Improvements.
- Process health scans feed Agent Jobs, Ops, and Command Center.

Schedulers are not activated by this UI work. Future scheduler activation must go through Approvals.

Deterministic capture/enrichment results flow back into department project cards through the canonical `project_enrichment` payload. NotebookLM enrichment can later write the same payload with `enrichment_source=notebooklm`.

NotebookLM is optional. `scripts/intake/notebooklm_connector.py` currently supports dry-run/status reports only and fails safely with `NotebookLM connector not configured` when no approved connector/session exists.

The daily department digest is manual-only for now:

```bash
python3 scripts/automation/run_daily_department_digest.py --dry-run --limit-per-feeder 3 --no-external-ai --skip-capture
```

## Department Feeder Layer

The feeder layer defines how manual/scheduled processes will feed department project boards. It is a registry plus a dry-run-first manual runner:

- Registry: `src/config/nexusDepartmentFeeders.ts`
- Runner: `scripts/automation/run_department_feeder.py`

The runner currently reports feeder targets and proof events. Live scheduler activation is intentionally disabled until Ray approves it.

## C. Review/Approval Mode

Risky next actions belong in Approvals:

- Publish.
- Send email/message.
- Trade.
- Deploy.
- Scheduler activation.
- Raw local/v1 execution.
- Client-facing promotion.
- Sensitive data/external AI.

Safe internal actions may create `task_requests` or update internal metadata. Risky actions create `approvals`. Existing approval gates, universal action policy, Hermes persistence, capture worker, Source Intake, and safety gates remain intact.
