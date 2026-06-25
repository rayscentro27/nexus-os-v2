# Nexus — Source Intake & Review UI Plan

From `preview (1).html`. The Intake tab now renders `source-intake/SourceIntakeReviewPage.tsx`.

## Components
- `AddSourcePanel` — six source-type tiles (UI; picking fills the entry form). YouTube/idea marked
  "Supported (approved CLI)", others "Coming soon".
- `SourceEntryForm` — Submit files an approval-gated `task_request` (`research_source_intake`). It
  **does not capture in the browser** (capture stays CLI/approved). Firewall-checked before submit.
- `RecentSourcesTable` — **REAL** `research_sources` rows: title, type, transcript status, review
  status, score bar, category, destination, captured time. Shows the captured
  "Hermes SEO Agent OS…" source.
- `ReviewDetailPanel` — selected source's v1 rating (score, priority, tags, compliance note) +
  routing buttons (Promote to Opportunity Lab / Send to Creative / Mark Research Only / Park) that
  file `task_requests` (sign-off only), plus Ask Hermes (navigates to Command Center).
- `ConnectionStatus` card — truth-based: what works now / data sources / not connected yet.

## Real vs static
- Real: the table, the review detail, scores/categories/destinations (from `metadata`).
- Static: header status pills, Connection Status copy, source-type tiles.

## Safe actions only
Submit → task_request. Routing → task_request. Ask Hermes → navigate. **No browser capture, no
publish/send/trade, no scheduler.** Approved real capture remains the CLI wrapper
(`scripts/intake/run_existing_youtube_monitor.py --no-dry-run`).

## Next
Wire a "Run approved capture" action that creates a task_request Ray approves (then a worker runs the
CLI), and add transcript/file upload parsing.
