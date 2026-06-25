# Nexus — Capture Queue Worker

`scripts/intake/run_capture_queue_worker.py` — bounded, manual, SAFE. Closes the Source Intake
capture loop by running the audited YouTube wrapper once per queued item.

## What it processes (task_requests)
- **Safe queued** (default): `task_type=youtube_capture_request`, `status in (requested,queued)`,
  `payload.approval_required=false`, `payload.source_capture_policy=safe_admin_submitted_capture_v1`,
  `payload.capture_status in (queued|requested|null)`.
- **Approved review-required** (only): `payload.approval_required=true` AND a **linked `approvals`
  row with status `approved`** (matched by `payload.task_request_id`). Never auto-approves.

## Hard validation (refuses otherwise)
Public YouTube **video** URL only (`watch?v=…` / `youtu.be/…`) — rejects playlists, channels, `/@`,
search, broad scrape. Refuses any payload flag for publish/send/trade/deploy, scheduler, v1 worker,
or external AI. Only processes items already in the queue — never an arbitrary URL.

## Run
```
# dry-run (no capture, no writes):
python3 scripts/intake/run_capture_queue_worker.py --once --limit 1 --dry-run --no-external-ai
# one real queued safe item:
python3 scripts/intake/run_capture_queue_worker.py --once --limit 1 --no-dry-run --no-external-ai
```
Flags: `--once --limit N` (cap 3) · `--dry-run`/`--no-dry-run` · `--no-external-ai` (default) ·
`--request-id` · `--source-url` (filter to a queued item) · `--approved-only` · `--safe-queue-only`
· `--json` · `--report-path`.

## On process (live)
1. `task_requests` → `status=running`, `payload.capture_status=running`; proof `capture_worker_started`.
2. Runs once: `run_existing_youtube_monitor.py --source-url "<URL>" --once --limit 1 --no-external-ai
   --write-events --no-dry-run` (transcript-only, no media, no external AI).
3. Parses the wrapper output for `research_source_id` / score / category / destination.
4. On success → `status=done`, `payload.capture_status=captured`, `result_summary`, `completed_at`,
   `research_source_id`, `nexus_event_id`; proof `capture_worker_completed`.
5. On failure → `status=failed`, `payload.capture_status=failed`, safe error summary; proof
   `capture_worker_failed`. No endless retry.

## Tables written (live only)
`task_requests` (status/payload/result), `nexus_events` (proofs), and — via the wrapper —
`research_runs`/`research_sources`/`intake_events`/`transcript_reviews`. **Never** the v1 `research`
table, social tables, or `social_accounts`.

## Never
publish/send/trade/deploy · flip publish_enabled · social publish jobs · scheduler/daemon · v1
workers · summarize.py / external AI · broad scraping · browser execution · auto-approve. Not run on
import; no cron/launchd. Not integrated into `nexus_runner.py` (that runner is for `agent_jobs`).

## UI
Source Intake "Capture Queue" shows queued → running → captured/done → failed with result summary +
linked source. Approval-required items also appear in Approvals.

## Next
Add an Approvals-UI "approve & queue" button (flip a review-required request's linked approval to
approved, so this worker can then process it). Optional: a manual operator command to run the worker
on a single approved item.
