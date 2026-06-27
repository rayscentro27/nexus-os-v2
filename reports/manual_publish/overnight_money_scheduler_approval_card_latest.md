# Overnight Money Scheduler Approval Card

- timestamp: 2026-06-27T11:29:23.462357+00:00
- status: ok
- dry_run: True
- external_action: false · money_spent: false · level_3_blocked: true

## Approve Overnight Money Opportunity Run Proposal
Approve the PROPOSAL to run the all-night money runner nightly in dry-run. Approval does NOT install or activate a scheduler — activation remains a separate, approval-gated step.

- proposed command: `python3 scripts/night_run/run_all_night_internal_tests.py --dry-run --cycles 8 --interval-minutes 45 --json`
- schedule: daily @ 22:00 local · 8 cycles · 45m interval
- risk: medium
- recommended decision: Approve proposal for future scheduler activation, but keep activation separate.

### What it CAN do
- Run internal dry-run research/scoring/drafting in cycles.
- Build a rolling morning agenda and Hermes brief.
- Run the safety verifier and write reports.

### What it CANNOT do
- Install cron/launchd/systemd or create a daemon.
- Publish, send, post, upload, deploy, charge, or spend.
- Contact clients, activate partner/payment links, connect Client Vault, or use raw client data.
