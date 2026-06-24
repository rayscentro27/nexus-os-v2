# Nexus Mac Agent Execution Bridge Plan

Date: 2026-06-24

## Purpose

The bridge lets Ray ask Hermes, Claude, or Codex for work in plain language while keeping actual Mac execution bounded, observable, and approval-gated.

The bridge must not become a hidden shell. It should translate approved work into allowlisted Nexus commands, run them locally, and write safe proof back to Supabase and reports.

## Flow

1. Ray gives a prompt to Hermes, Claude, or Codex.
2. The agent classifies the request into a Nexus capability, such as watch loop, report generation, creative draft, landing page package, safe status check, or queued job.
3. If the request is risky or external-facing, the agent creates an approval or task request instead of executing.
4. After explicit approval, the local bridge selects an allowlisted command.
5. The bridge runs the command with bounded arguments, timeout, and lock protection.
6. Output is reduced to a safe summary.
7. Proof is written to `nexus_events`, relevant status tables, and/or `reports/runtime`.
8. Nexus UI displays the result through the relevant tab and the Events Feed.
9. Hermes can explain the result from safe report summaries and ledger rows.

## Tool Selection

The agent should choose commands from a registry, not from arbitrary shell text. Each registry entry should define:

- command key
- exact executable and allowed arguments
- required environment names, names only
- timeout
- lock key
- whether network is allowed
- whether Supabase writes are allowed
- whether approval is required
- output redaction rules
- tables/reports written

Examples:

- `nexus_watch`: `npm run nexus:watch`
- `nexus_runner_dry_run`: `python3 scripts/nexus_runner.py --once --limit 1 --dry-run`
- `facebook_token_status`: `python3 scripts/social/facebook_token_status.py`
- `creative_score_assets`: `python3 scripts/creative/score_creative_assets.py`
- `oanda_demo_status`: demo connection check only

## Allowlist Rules

Allowed by default:

- read-only status checks
- local deterministic scoring
- report generation
- dry-run runners
- Supabase proof/event writes for safe operations

Requires explicit approval:

- approval status changes
- job creation for public-facing outputs
- email test sends
- social publishing
- deploys
- any demo/paper order

Never allowed:

- live/funded trading
- paid ads or boosted posts
- mass email
- scraping or exposing private customer files
- printing secrets
- committing `.env`
- service-role key in frontend
- broad RLS weakening
- unbounded daemon loops
- production Oracle restarts without a specific approved maintenance plan

## Approval Handling

Hermes can propose an action and store a pending action, but it does not execute it. Approval phrases such as "approved" or "yes please" resolve only against the current pending action.

Approval records should include:

- action type
- safe summary
- worker assignment
- allowed data scope
- forbidden data
- Hermes visibility
- required runtime gate
- status

The bridge checks approval status immediately before execution.

## Output Handling

The bridge writes:

- `nexus_events` proof row
- `agent_jobs` result/update when job-based
- relevant domain table update when safe
- `reports/runtime` log/report
- optional `reports/manual_publish` package for manual next steps

Outputs sent to Hermes must be summaries only. Raw secrets, tokens, customer private data, SSNs, credit reports, bank docs, tax docs, passwords, and reset tokens must never be included.

## UI Display

The Nexus UI should show:

- command status in Events Feed
- jobs in Agent Jobs
- approvals in Approvals
- report summaries in Ops/System Health
- revenue packages in Creative Studio or GoClear/Apex
- integration blockers in Integrations

Every UI data surface should show whether it is connected, blocked by auth/RLS, empty, or query-failed.

## First Implementation Step

Create a Supabase-backed `mac_command_registry` or a checked-in registry file, then add one bridge command: `nexus_watch`. It should run `npm run nexus:watch` with a lock, timeout, redaction, and proof write. Add more commands only after that path is observable in the UI.
