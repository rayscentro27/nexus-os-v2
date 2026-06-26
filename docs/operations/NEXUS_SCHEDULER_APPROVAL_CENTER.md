# Nexus Scheduler Approval Center

Scheduler Approval Center is a proposal layer only. It does not activate cron, launchd, systemd, persistent loops, or recurring jobs.

Scheduler activation is always **Level 2 (approval-gated)** — see
[NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md). No scheduler is ever activated by Nexus.

Candidate schedules:

- Daily Department Digest
- Weekly YouTube Watched Resource Check
- Weekly YouTube Research Report
- Weekly Hermes Prep Brief
- Weekly GoClear Revenue Report
- Weekly Trading Paper Report
- Weekly Automation Control Report
- Weekly SEO Opportunity Report
- Weekly Affiliate Opportunity Report
- Weekly Client Readiness Report
- Weekly Ops Improvement Report

Each candidate includes: category, automation level, proposed frequency, allowed writes, forbidden
actions, rollback/disable command, proof/report path, owner, risk level, Ray-approval-required,
current status (proposed/approved/blocked/active/disabled), connector-required,
external-API-required, and whether a high-risk guard applies.

Command:

```bash
python3 scripts/automation/generate_scheduler_approval_candidates.py --dry-run --limit 11 --json
```
