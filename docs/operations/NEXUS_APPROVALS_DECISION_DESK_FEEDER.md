# Nexus Approvals Decision Desk Feeder

`approvals_decision_desk_feeder` creates advisory decision cards from existing `approvals` rows and `task_requests` marked approval-required.

It writes `task_requests.task_type=approval_decision_project` and `nexus_events.action=approval_decision_project_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id approvals_decision_desk_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id approvals_decision_desk_feeder --no-dry-run --limit 5 --no-external-ai
```

The feeder never approves, rejects, publishes, sends, deploys, trades, or modifies an approval. Recommended decisions are advisory only.
