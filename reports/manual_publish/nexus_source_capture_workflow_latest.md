# Nexus — Source Capture Workflow (report)

- generated_at: 2026-06-25 · build PASS · watch PASS

## What was added
A safe **Run Approved Capture** workflow in Source Intake & Review:
- `SourceEntryForm` now validates a public YouTube URL, files an **approval-gated `task_request`**
  (`youtube_capture_request`) with the exact CLI command a worker runs after approval, and writes a
  `nexus_events` proof. Non-YouTube submits file a `research_source_intake` request.
- New **Pending Capture Requests** rail (`PendingCaptureRequests.tsx`) lists requested
  `task_requests` (read-only) with the command preview and "awaiting approval".
- Helper text added verbatim: "Browser capture is disabled. Approved capture runs through the local
  CLI wrapper after Ray approval."

## Behavior (verified)
- Submitting a YouTube URL → creates a `task_request` (status `requested`) + proof event; shows
  "Pending approval — capture will run through the local CLI wrapper after approval." + the id; the
  request appears in the Pending rail.
- **No browser capture** (no yt-dlp), no external AI, no scheduler, no v1 jobs, no publish/send/trade.

## Storage
`task_requests` (existing table, admin RLS). **No schema change** — `payload` carries source_url,
source_type, title, target_use, priority, tags, requested_by, created_at, capture_command_preview,
approval_required, risk_level, external_ai=false, scheduler=false, v1_jobs_touched=false.

## Preserved
research_sources read, row selection, Review Detail, Hermes Review panel, captured YouTube records,
deterministic score/category/destination display.

## Live review (Part 1)
Deploy `bd9fc9a` is current (bundle hash matches local build); pages HTTP 200; polish markers present
(`nx-mc-grid`, System Awareness, Hermes Review, Source Intake & Review). See
`nexus_live_ui_review_latest.md`. No blocking layout bug found.

## Safety
build PASS · watch PASS · no capture · no scheduler · v1 untouched · no publish/send/trade/deploy ·
approval `13eafcab` pending · FB `publish_enabled` false · no secrets · `.env` not committed · no
schema/RLS change.

## Next
Build the approved-capture worker (poll approved `youtube_capture_request` → run the stored command
once → set `done` + `result_summary` + proof) and an Approvals-UI approve button.
