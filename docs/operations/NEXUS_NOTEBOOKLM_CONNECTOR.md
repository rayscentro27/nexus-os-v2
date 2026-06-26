# Nexus NotebookLM Connector

NotebookLM support is optional. Nexus can run without NotebookLM by using Source Intake, deterministic enrichment, and the local capture worker.

## Current Status

`scripts/intake/notebooklm_connector.py` is a status/report foundation only. It does not store cookies, tokens, session files, browser profiles, or credentials in the repo.

Dry-run status:

```bash
python3 scripts/intake/notebooklm_connector.py --dry-run --mode status --json
```

If no approved connector/session is configured, it returns:

`NotebookLM connector not configured`

This is safe and should not fail builds.

## Future Modes

The CLI reserves these modes:

- `status`
- `add-source`
- `export-summary`

Live `add-source` and `export-summary` are intentionally blocked until Ray approves a connector and a credential/session storage policy outside the repo.

## Boundaries

- no cookies/tokens/session files in repo
- no browser automation in this foundation pass
- no broad scraping
- no external AI on private/customer/sensitive text
- no mandatory dependency on NotebookLM
- fallback remains local direct enrichment and capture worker

## Direct Source Enrichment Fallback

Use metadata-first direct enrichment for one explicit public source:

```bash
python3 scripts/intake/direct_source_enrichment.py --source-url "https://example.com/test-source" --title "Safe Test Source" --dry-run --no-external-ai --json
```

Live mode writes only `research_sources.metadata.project_enrichment` and `nexus_events` proof.
