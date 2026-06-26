# Nexus Scheduler Approval Center

Scheduler Approval Center is a proposal layer only. It does not activate cron, launchd, systemd, persistent loops, or recurring jobs.

Candidate schedules:

- Weekly YouTube watched resource check
- Weekly YouTube top report
- Daily Department Digest
- Weekly Hermes prep brief
- Weekly GoClear Revenue Hub report
- Weekly Trading Lab paper performance report

Each proposal includes allowed writes, forbidden actions, risk level, and rollback/disable plan.

Command:

```bash
python3 scripts/automation/generate_scheduler_approval_candidates.py --dry-run --limit 10 --json
```
