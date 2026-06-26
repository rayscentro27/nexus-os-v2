# Nexus Creative Studio Feeder

`creative_studio_project_feeder` creates draft-only Creative Studio cards from existing `creative_assets`, `social_posts`, and enriched public research related to content, campaigns, social, copywriting, video, creative, brand, offers, or marketing.

It writes `task_requests.task_type=creative_studio_project` and `nexus_events.action=creative_studio_project_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id creative_studio_project_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id creative_studio_project_feeder --no-dry-run --limit 5 --no-external-ai
```

Publishing, email sending, social posting, and external AI are not executed. Public use remains approval-gated.
