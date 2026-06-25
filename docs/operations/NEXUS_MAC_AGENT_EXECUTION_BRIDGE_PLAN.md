# Nexus Mac Agent Execution Bridge Plan

Date: 2026-06-24

## Current Reality

Nexus OS v2 has the pieces for a safe local execution bridge, but the bridge is not complete.

Working pieces:

- `agent_jobs` table exists.
- UI can create some jobs.
- Hermes can create `task_requests` after approval and some `agent_jobs` through handler paths.
- `scripts/nexus_runner.py` manually consumes jobs.
- `scripts/runner_handlers/__init__.py` is an allowlist.
- Runner writes job output, heartbeats, and `nexus_events`.
- Agent Jobs and Events Feed can display results.

Not yet working:

- No secure UI button that runs local Mac commands.
- No daemon controlled by nexus-os-v2.
- No explicit command registry table.
- No signed request/claim protocol between UI and Mac worker.
- No unified audit display for command stdout/stderr summaries.
- Existing `nexus-ai` and `mac-mini-worker` processes are outside nexus-os-v2 control.

## Target Flow

1. Ray gives a prompt to Hermes, Claude, or Codex.
2. Hermes classifies the request and either answers, creates a task request, or queues an approved job.
3. Risky work creates an approval first.
4. A local bridge reads only approved/allowlisted jobs.
5. The bridge runs a fixed command with fixed args, timeout, lock, and redaction.
6. It writes output summaries to `agent_jobs`, `nexus_events`, and reports.
7. Nexus UI displays the result.
8. Hermes can explain only safe summaries.

## Command Allowlist

Initial allowlist should include only:

- `nexus_watch`: `npm run nexus:watch`
- `nexus_runner_dry_run`: `python3 scripts/nexus_runner.py --once --limit 1 --dry-run`
- `transcript_review`: `python3 scripts/intake/review_transcript.py --intake-event-id <id>`
- `creative_score_assets`: `python3 scripts/creative/score_creative_assets.py`
- `facebook_token_status`: `python3 scripts/social/facebook_token_status.py`
- `model_route_dry_run`: `python3 scripts/hermes/request_model_route.py --dry-run`

Do not include real publish, live trade, deploy, restart, or scheduler commands in v1.

## Approval Rules

Always require approval for:

- social publishing
- email sends
- deploys
- demo/paper orders
- scheduler start
- anything touching customer-private data
- any command not in the allowlist

Never allow:

- live/funded trading
- paid ads
- mass email
- broad RLS weakening
- printing secrets
- committing `.env`
- service-role key in browser
- Oracle production restarts from UI

## Recommended First Implementation

Create one safe bridge path:

1. Add `mac_command_registry` or checked-in JSON registry.
2. Add one command: `nexus_watch`.
3. Add UI card: "Run one safe watch pass".
4. Runner writes `agent_jobs.output`, `nexus_events`, and report path.
5. Hermes can explain the result.

Only after that works should more commands be added.
