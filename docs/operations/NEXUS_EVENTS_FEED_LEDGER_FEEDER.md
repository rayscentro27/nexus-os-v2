# Nexus Events Feed Ledger Feeder

`events_feed_ledger_feeder` creates proof/history summary cards from recent `nexus_events`.

It writes `task_requests.task_type=event_ledger_project` and `nexus_events.action=event_ledger_summary_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id events_feed_ledger_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id events_feed_ledger_feeder --no-dry-run --limit 5 --no-external-ai
```

The feeder is read/summarize only. It does not modify historical events and now skips department-feeder-created events to avoid recursive ledger chains. It also skips trading/Oanda events in this pass.
