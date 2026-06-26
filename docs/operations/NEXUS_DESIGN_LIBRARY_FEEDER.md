# Nexus Design Library Feeder

`design_library_project_feeder` creates Design Library cards from existing creative assets, design inspiration sources, feature design packets, UI quality reviews, and design-related enriched research.

It writes `task_requests.task_type=design_library_project` and `nexus_events.action=design_library_project_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id design_library_project_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id design_library_project_feeder --no-dry-run --limit 5 --no-external-ai
```

Organizing and design review are safe. Public posting, usage claims, and image generation remain out of scope.
