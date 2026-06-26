# Nexus GoClear Revenue Hub

GoClear Revenue Hub is the foundation for showing GoClear/Apex revenue-pipeline cards in Nexus without connecting payment processors, affiliate APIs, email sending, or public offer changes.

## Metric Model

Defined in `src/config/goclearRevenueMetrics.ts` and supported by `src/lib/goclearRevenueHub.ts`.

Supported metric areas:

- readiness review leads
- `$97` readiness review purchases
- `$297/$497` upgrades
- subscription prospects
- monthly recurring revenue
- funding applications
- commission opportunities
- affiliate/referral clicks
- affiliate/referral conversions
- Nav/business credit partner referrals
- Beehiiv/newsletter growth
- Pictory/content affiliate
- SEO/content leads
- booked calls
- estimated revenue potential
- actual revenue if safely available

## Feeder

Dry-run:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id goclear_revenue_hub_feeder --dry-run --limit 5 --no-external-ai
```

Bounded live:

```bash
python3 scripts/automation/run_department_feeder.py --feeder-id goclear_revenue_hub_feeder --no-dry-run --limit 5 --no-external-ai
```

The feeder reads existing safe `task_requests`, enriched `research_sources`, and local GoClear reports. It writes internal `task_requests.task_type=goclear_revenue_metric_project` and `nexus_events.action=goclear_revenue_hub_metrics_updated`.

## Safety

The feeder does not:

- call Stripe/payment processors
- call affiliate APIs
- send email
- publish social posts
- deploy pages
- charge anyone
- change offers publicly
- use external AI

## UI

The GoClear / Apex tab now has a NotebookLM-style Revenue Hub project-card workspace. If no live metrics exist, it shows the feeder and next action rather than fake data.

## Next Recommendation

Choose the first real safe source of revenue truth: form submissions, Stripe read-only reporting, affiliate dashboard export, or manually reviewed CSV.
