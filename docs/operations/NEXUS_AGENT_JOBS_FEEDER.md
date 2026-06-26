# Nexus Agent Jobs Feeder

`agent_jobs_process_feeder` creates Automation Workforce cards from existing `agent_jobs`, `task_requests`, and local report names.

It writes `task_requests.task_type=agent_job_project` and `nexus_events.action=agent_job_project_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id agent_jobs_process_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id agent_jobs_process_feeder --no-dry-run --limit 5 --no-external-ai
```

This feeder is observability only. It does not run jobs, schedule jobs, start processes, or execute local commands.
