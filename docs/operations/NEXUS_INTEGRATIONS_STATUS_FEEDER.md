# Nexus Integrations Status Feeder

`integrations_status_feeder` creates Connections Department cards from `integration_registry`, `system_health`, and the local watch report when available.

It writes `task_requests.task_type=integration_status_project` and `nexus_events.action=integration_status_project_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id integrations_status_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id integrations_status_feeder --no-dry-run --limit 5 --no-external-ai
```

The feeder never connects accounts, changes credentials, prints secrets, or calls external APIs. It skips trading/Oanda connectors in this pass.
