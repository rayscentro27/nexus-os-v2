# Nexus Command Center Feeder

`command_center_summary_feeder` creates one Executive Office summary card from existing `task_requests`, `approvals`, `nexus_events`, and feeder status.

It writes `task_requests.task_type=command_center_summary` and `nexus_events.action=command_center_summary_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id command_center_summary_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id command_center_summary_feeder --no-dry-run --limit 5 --no-external-ai
```

The feeder summarizes active departments, needs review, blocked items, pending approvals, and top recommendation. It does not execute actions or modify approvals.
