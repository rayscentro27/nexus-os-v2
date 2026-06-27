# Nexus Overnight Money Opportunity Research Engine

Nexus works overnight as a money-opportunity research engine: it researches (curated/internal, not
scraped), scores, classifies, drafts assets, and prepares a morning package for Ray + Hermes — all
internal, draft-only, and approval-gated. Nothing publishes, sends, charges, spends, contacts,
trades, mails, files, or applies.

## What it researches

Credit repair / business funding / business credit trends, funding readiness pain points, SmartCredit
+ AnnualCreditReport.com angles, online business banking + funding-path banks (BofA/Chase/credit
unions/community banks), business setup pain points (LLC/EIN/address/phone/domain/email/DUNS/vendor),
DocuPost/USPS education, competitor pricing/offers, TikTok/IG/FB hooks, landing page angles,
affiliate programs, subscription upsells, client reminder/revenue-risk, funding commission, and
post-funding growth.

## Scoring + opportunity types

Source: `scripts/research/money_opportunity_model.py`. Each item scores revenue/speed/cost/risk,
client value, affiliate/subscription/funding-commission potential, content/landing/TikTok/IG-FB
potential, and Hermes discussion value; a composite `overall_score` ranks them. Each is classified
into one or more opportunity types: direct_offer, monthly_subscription, affiliate_opportunity,
client_workflow_improvement, content_opportunity, landing_page_opportunity, hermes_discussion_topic,
ray_review_approval_item.

## Reports (morning package)

`money_opportunity_research`, `money_opportunity_scoreboard`, `money_opportunity_launch_plan`,
`overnight_creative_asset_queue`, `overnight_landing_page_ideas`, `overnight_social_video_ideas`,
`overnight_affiliate_opportunity_queue`, `best_money_opportunity_creative_package`,
`hermes_money_opportunity_brief`, `ray_morning_money_agenda`, `ray_hermes_morning_discussion_agenda`
(MD in `reports/manual_publish/`, JSON in `reports/runtime/`).

## All-night runner + safety

```
python3 scripts/night_run/run_all_night_internal_tests.py --dry-run --cycles 1 --interval-minutes 0 --json
python3 scripts/safety/verify_no_external_execution.py --dry-run --json
```

The runner executes phases in order: automation/access/vault/workflow → market/revenue → money
opportunity engine + creative → Hermes final brief + Ray morning agenda. The safety verifier scans
every runtime report's safety flags and fails if any external-action flag is true (or
`level_3_blocked` is false).

## Hermes

Hermes acts as Ray's private business advisor in plain language (why it matters, how it makes money,
what to create, what needs approval, what could go wrong, what stays blocked, and how it connects to
GoClear/Apex revenue, subscriptions, affiliate revenue, and funding commissions). Hermes uses only
sanitized signals, public/curated research, mock workflow data, and generated reports — never raw
client data.

## Command Center

`MoneyOpportunityCard` shows the top opportunity, fastest launch path, best creative/affiliate/landing/
social, approval needed, and the Hermes recommendation.

## Safety

Every report sets `publish_status: draft_only`, `approval_required: true`,
`external_action_performed: false`, `client_contacted: false`, `money_spent: false`,
`client_charged: false`. Level 3 actions stay blocked.
