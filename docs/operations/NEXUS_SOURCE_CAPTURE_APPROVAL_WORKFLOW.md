# Nexus — Source Capture Approval Workflow

Closes the safe capture loop from the UI **without** running capture in the browser.

```
Source Intake UI (Submit YouTube URL)
  → validate it's a public YouTube URL
  → file an approval-gated task_request (youtube_capture_request) + nexus_events proof
  → [Ray approves]  ← human gate (Approvals UI / Supabase)
  → a local worker runs the CLI wrapper command stored in the request
  → v2 Supabase rows (research_sources / intake_events / transcript_reviews / nexus_events)
  → Source Intake "Recent Sources" shows the captured + reviewed source
```

## 1. UI submission
`source-intake/SourceEntryForm.tsx`. On Submit:
- Firewall check (refuses private-data-looking input).
- If `source_type=youtube_video`: validate `youtube.com/watch?v=…` or `youtu.be/…`.
- Files a `task_request` (see below) and writes a `nexus_events` proof
  (`youtube_capture_requested`, status `pending`).
- Shows: **"Pending approval — capture will run through the local CLI wrapper after approval."** +
  the `task_request` id. The request appears in the **Pending Capture Requests** rail.
- **Never** runs yt-dlp / captures in the browser.

## 2. Where requests are stored
Supabase **`task_requests`** (admin RLS; migration 0011). No schema change was needed — the existing
columns cover it (`task_type`, `sensitivity`, `assigned_worker_type`, `hermes_visibility`, `status`,
`payload`, `created_at`). The rich capture details live in `payload`.

### task_request shape (youtube_capture_request)
```
task_type: youtube_capture_request
status: requested
sensitivity: internal_summary
assigned_worker_type: research_worker
hermes_visibility: summary
payload: {
  action_type: youtube_capture_request,
  source_type: youtube_video,
  source_url, title, target_use, priority, tags[], requested_by, created_at,
  capture_command_preview: "python3 scripts/intake/run_existing_youtube_monitor.py
      --source-url \"<URL>\" --once --limit 1 --no-external-ai --write-events --no-dry-run",
  approval_required: true, risk_level: medium, external_ai: false, scheduler: false,
  v1_jobs_touched: false
}
```

## 3. How approval should work
Ray reviews the request (Approvals UI or directly in Supabase) and sets the request to approved.
**Approval is a human gate** — the UI never auto-approves and never executes. (Today the request is
`status=requested`; a follow-up build adds the approve→run binding.)

## 4. What the worker runs (after approval)
Exactly the stored `capture_command_preview`:
```
python3 scripts/intake/run_existing_youtube_monitor.py --source-url "<URL>" \
    --once --limit 1 --no-external-ai --write-events --no-dry-run
```
That wrapper is the audited, bounded, transcript-only (no media), no-external-AI capture that writes
v2 tables + a proof. A worker should poll `task_requests` for approved `youtube_capture_request`
rows and run that command on the local host (where yt-dlp lives) — not in the browser, not in an
Edge Function.

## 5. Why browser capture is disabled
yt-dlp/transcript capture needs a local binary + filesystem and must respect rate limits; running it
from the browser (or a public Edge Function) is unsafe and impossible. So the browser only **files a
request**; capture stays on the local CLI behind Ray's approval.

## 6. Safety boundaries
No browser capture · no yt-dlp from the browser · no external AI on transcript text · no
publish/send/trade/deploy · no scheduler · no v1 jobs touched · no schema/RLS change · firewall-checked
input · approval required before any capture.

## 7. Next step (worker execution after approval)
Build a small **approved-capture worker**: poll `task_requests` where
`task_type=youtube_capture_request AND status=approved`, run the stored command once, set the row to
`done` with a `result_summary`, and write a `nexus_events` proof. Add an Approvals-UI button that
flips the request to approved (no execution in the browser).

## Update (policy + visibility, 2026-06-25)
- Safe admin-submitted capture is now a **Capture Queue** item (`approval_required=false`), not an
  approval. See `NEXUS_SOURCE_CAPTURE_POLICY.md`.
- Review-required items file a linked `approvals` row so they show in the Approvals tab. See
  `NEXUS_APPROVAL_VISIBILITY_MODEL.md` (root cause: Source Intake wrote `task_requests`, Approvals
  reads `approvals`).
- UI: "Pending Approval" rail → **Capture Queue**; shows Safe capture vs Approval required + next step.

## Worker (built 2026-06-25)
`scripts/intake/run_capture_queue_worker.py` polls `task_requests` for safe queued (and approved
review-required) capture items and runs the wrapper once each. See `NEXUS_CAPTURE_QUEUE_WORKER.md`.
Manual/bounded/dry-run-default; not scheduled; not in the browser.
