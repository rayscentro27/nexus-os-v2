# Nexus SEO / Marketing Feeder

`seo_marketing_project_feeder` creates Growth Department cards from existing SEO rows, social drafts, and enriched public research related to SEO, marketing, content, keywords, funnels, landing pages, GoClear/Apex, and lead generation.

It writes `task_requests.task_type=seo_marketing_project` and `nexus_events.action=seo_marketing_project_created`.

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id seo_marketing_project_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id seo_marketing_project_feeder --no-dry-run --limit 5 --no-external-ai
```

Drafts, reports, and research are safe. Publishing site changes, emails, ads, and social posts remain approval-gated and unexecuted.
