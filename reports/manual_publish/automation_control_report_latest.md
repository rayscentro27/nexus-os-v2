# Nexus Automation Control Center

- generated_at: 2026-06-27T00:17:48.998956+00:00
- dry_run: True
- ok: True
- scheduler_started: false
- publish_send_trade_deploy: false
- external_ai_called: false
- media_download: false
- broad_scrape: false

## Counts
- total_categories: 30
- level_1_internal: 30
- level_2_gated: 26
- level_3_blocked: 30
- schedule_ready: 8
- scheduler_approval_required: 11
- connector_required: 5
- external_api_required: 5
- high_risk_guard_required: 30

## Hermes recommended next automation
Enable schedule-ready Level 1 reports (research/SEO/affiliate/trading-paper) as manual runs; keep all connectors and schedulers approval-gated.

## Top automation risks
- Live trading
- Broker order execution
- Funded account actions
- Raw auto_executor exposure
- Payment charge
- Payment refund

## Schedule-ready categories
- research_source_intake
- youtube_research
- seo_marketing
- affiliate_marketing
- content_opportunity_lab
- goclear_revenue_hub
- trading_lab
- monitoring_health

## Needs Ray approval
- research_source_intake
- youtube_research
- seo_marketing
- affiliate_marketing
- content_opportunity_lab
- creative_studio
- design_library
- goclear_revenue_hub
- goclear_apex_client_intake
- credit_repair_funding_guidance
- opportunity_lab
- agent_jobs
- integrations
- approvals
- ray_review_queue
- hermes_jarvis
- scheduler_automation
- production_deployment
- email_sms_dm_social
- ads_spend
- database_supabase
- notebooklm_research_library
- grants_funding_opportunities
- business_credit_vendor_accounts
- client_portal
- admin_tenants_users

## Blocked / needs separate contract
- RLS weakening
- YouTube media downloads
- ad spend activation
- auto-approving high-risk items
- auto-executing queued items
- broad scraping
- broad scraping into imports
- broad scraping of partner sites
- broker execution
- bulk send
- bypassing approval gates
- client data exposure externally
- committing .env/secrets
- compliance-sensitive claims published without review
- connecting sensitive systems
- credential changes
- credential changes without review
- cron/launchd/systemd creation without approval
- destructive DB writes
- destructive admin actions
- destructive job actions
- destructive ledger writes
- destructive production actions
- destructive remediation without approval
- external AI on credit-sensitive data
- external AI on customer data
- external AI on sensitive data
- external AI on sensitive/customer data
- external AI on sensitive/private/customer data
- funded account actions
- live trading
- payment charges
- payment/spend actions
- production deploy of site changes
- production deploys
- raw auto_executor exposure
- raw command execution from browser
- secret printing
- spam automation
- spend on paid creative tools
- spend/commitment actions
- tampering with proof history
- tenant isolation bypass

## What Ray can ignore for now
Internal scoring/routing/reports and paper-only trading research — these run autonomously and do not need per-item approval.

## Per-category
### Research / Source Intake (research_source_intake) — source_intake
- Level 1 (autonomous): source intake enrichment, scoring, routing, internal cards, internal reports
- Level 2 (approval-gated): connector activation for live source pulls, scheduler activation
- Level 3 (blocked): broad scraping, external AI on sensitive/private/customer data
- next: Keep enrichment/scoring autonomous; leave live connectors and scheduler as approval-gated.

### YouTube Research (youtube_research) — source_intake
- Level 1 (autonomous): metadata check (placeholder/fallback), transcript review from local samples, scoring/routing, internal reports, Hermes prep brief
- Level 2 (approval-gated): metadata connector activation, scheduler activation, publish of derived content
- Level 3 (blocked): YouTube media downloads, broad scraping
- next: Run metadata/transcript dry-runs; keep connector + scheduler approval-gated.

### SEO / Marketing (seo_marketing) — growth
- Level 1 (autonomous): SEO keyword scoring, opportunity scoring, internal cards/reports
- Level 2 (approval-gated): publishing to site, site/production change, scheduler activation
- Level 3 (blocked): production deploy of site changes, external AI on sensitive data
- next: Keep keyword scoring autonomous; gate any publish/site change.

### Affiliate Marketing (affiliate_marketing) — opportunity_lab
- Level 1 (autonomous): affiliate opportunity scoring, partner research, internal cards/reports
- Level 2 (approval-gated): publishing affiliate content, outbound partner contact
- Level 3 (blocked): spend/commitment actions, broad scraping of partner sites
- next: Keep opportunity scoring autonomous; gate outbound/publish.

### Content Opportunity Lab (content_opportunity_lab) — growth
- Level 1 (autonomous): content opportunity scoring, experiment cards, internal reports
- Level 2 (approval-gated): publishing content, sending content, scheduler activation
- Level 3 (blocked): external AI on sensitive/customer data
- next: Keep experiment cards autonomous; gate publish/send.

### Creative Studio (creative_studio) — creative_studio
- Level 1 (autonomous): draft creative generation, internal review cards, internal reports
- Level 2 (approval-gated): publishing creative, sending creative to clients, ad creative activation
- Level 3 (blocked): external AI on sensitive/customer data, spend on paid creative tools
- next: Keep drafting autonomous; gate publish/send/client delivery.

### Design Library (design_library) — design_library
- Level 1 (autonomous): design library organization, tagging, internal cards/reports
- Level 2 (approval-gated): publishing assets externally, client delivery
- Level 3 (blocked): external AI on sensitive/customer data
- next: Keep organizer autonomous; gate external delivery.

### GoClear Revenue Hub (goclear_revenue_hub) — opportunity_lab
- Level 1 (autonomous): internal revenue metric cards, internal reports, scoring
- Level 2 (approval-gated): lead contact, payment-link creation, campaign publishing, scheduler activation
- Level 3 (blocked): payment/spend actions, destructive DB writes
- next: Keep revenue cards autonomous; gate lead contact and payment links.

### GoClear / Apex Client Intake (goclear_apex_client_intake) — opportunity_lab
- Level 1 (autonomous): lead scoring, readiness checklist, internal cards/reports
- Level 2 (approval-gated): client notification, client contact, client-facing scheduling
- Level 3 (blocked): client data exposure externally, external AI on customer data
- next: Keep scoring/checklists autonomous; gate client contact.

### Credit Repair / Funding Guidance (credit_repair_funding_guidance) — opportunity_lab
- Level 1 (autonomous): internal guidance research, scoring, internal reports
- Level 2 (approval-gated): client-facing guidance delivery, client contact
- Level 3 (blocked): compliance-sensitive claims published without review, external AI on credit-sensitive data
- next: Keep research autonomous; gate all client-facing delivery; compliance review required.

### Opportunity Lab (opportunity_lab) — opportunity_lab
- Level 1 (autonomous): opportunity research, scoring, routing, internal cards/reports
- Level 2 (approval-gated): outbound contact, publishing, scheduler activation
- Level 3 (blocked): broad scraping, external AI on sensitive data
- next: Keep opportunity research autonomous; gate outbound/publish.

### Agent Jobs (agent_jobs) — agent_jobs
- Level 1 (autonomous): job status reporting, internal cards, internal reports
- Level 2 (approval-gated): scheduler activation, enabling persistent jobs
- Level 3 (blocked): raw auto_executor exposure, destructive job actions
- next: Keep status feeder autonomous; gate scheduler/persistent jobs.

### Integrations (integrations) — integrations
- Level 1 (autonomous): integration status reporting, internal cards/reports
- Level 2 (approval-gated): connector activation, OAuth setup, credential connection
- Level 3 (blocked): credential changes without review, connecting sensitive systems, secret printing
- next: Keep status feeder autonomous; gate connector activation.

### Events Feed / Proof Ledger (events_feed_proof_ledger) — events_feed
- Level 1 (autonomous): internal proof events, internal reports, ledger reads
- Level 2 (approval-gated): —
- Level 3 (blocked): destructive ledger writes, tampering with proof history
- next: Keep proof logging autonomous; never allow destructive ledger writes.

### Approvals (approvals) — approvals
- Level 1 (autonomous): approvals reporting (read-only), internal decision briefs
- Level 2 (approval-gated): Ray decision execution of an approved item
- Level 3 (blocked): auto-approving high-risk items, bypassing approval gates
- next: Keep approvals reporting autonomous; require Ray for each decision.

### Ray Review Queue (ray_review_queue) — command_center
- Level 1 (autonomous): queue building from true decisions, internal reports
- Level 2 (approval-gated): marking an item approved/executed
- Level 3 (blocked): auto-executing queued items
- next: Keep queue builder autonomous; never auto-execute queued items.

### Hermes / Jarvis (hermes_jarvis) — command_center
- Level 1 (autonomous): internal recommendations, prep briefs, summaries, internal reports
- Level 2 (approval-gated): Mac/computer-control bridge activation, outbound actions on Ray behalf
- Level 3 (blocked): raw command execution from browser, external AI on sensitive data
- next: Keep Hermes recommendations autonomous; gate any bridge/outbound execution.

### Trading Lab (trading_lab) — trading_lab
- Level 1 (autonomous): paper-only strategy research, backtest imports (local), scoring, internal reports
- Level 2 (approval-gated): —
- Level 3 (blocked): live trading, broker execution, funded account actions, raw auto_executor exposure
- next: Keep paper-only research autonomous; live execution stays blocked under its own contract.

### Scheduler / Automation (scheduler_automation) — ops_improvements
- Level 1 (autonomous): scheduler candidate proposals (proposal-only), internal reports
- Level 2 (approval-gated): scheduler activation, enabling persistent automation
- Level 3 (blocked): cron/launchd/systemd creation without approval
- next: Generate candidates only; never activate a scheduler without Ray approval.

### Production / Deployment (production_deployment) — ops_improvements
- Level 1 (autonomous): deploy readiness reports (internal)
- Level 2 (approval-gated): production change proposal
- Level 3 (blocked): production deploys, destructive production actions
- next: Keep readiness reporting autonomous; deploys stay blocked/gated.

### Email / SMS / DM / Social (email_sms_dm_social) — growth
- Level 1 (autonomous): draft messages, internal review cards
- Level 2 (approval-gated): sending email/SMS/DM, social posting, campaign publishing
- Level 3 (blocked): bulk send, spam automation
- next: Keep drafting autonomous; gate every send; block bulk/spam.

### Ads / Spend (ads_spend) — growth
- Level 1 (autonomous): ad opportunity research, internal cards/reports
- Level 2 (approval-gated): ad campaign activation proposal
- Level 3 (blocked): ad spend activation, payment charges
- next: Keep ad research autonomous; spend stays blocked/gated.

### Database / Supabase (database_supabase) — ops_improvements
- Level 1 (autonomous): read-only queries, internal schema reports
- Level 2 (approval-gated): schema change proposal
- Level 3 (blocked): destructive DB writes, RLS weakening, tenant isolation bypass
- next: Keep reads autonomous; block destructive DB and RLS changes.

### Files / Reports / Imports (files_reports_imports) — ops_improvements
- Level 1 (autonomous): local report generation, safe local imports, internal cards
- Level 2 (approval-gated): —
- Level 3 (blocked): committing .env/secrets, broad scraping into imports
- next: Keep local report generation autonomous; never commit secrets.

### NotebookLM / Research Library (notebooklm_research_library) — source_intake
- Level 1 (autonomous): library organization, internal summaries, internal reports
- Level 2 (approval-gated): connector activation
- Level 3 (blocked): external AI on sensitive/customer data
- next: Keep library organization autonomous; gate connector activation.

### Grants / Funding Opportunities (grants_funding_opportunities) — opportunity_lab
- Level 1 (autonomous): grant opportunity research, scoring, internal cards/reports
- Level 2 (approval-gated): application submission, outbound contact
- Level 3 (blocked): spend/commitment actions
- next: Keep grant research autonomous; gate submissions/outbound.

### Business Credit / Vendor Accounts (business_credit_vendor_accounts) — opportunity_lab
- Level 1 (autonomous): vendor research, scoring, internal cards/reports
- Level 2 (approval-gated): account application, outbound vendor contact
- Level 3 (blocked): credential changes, spend/commitment actions
- next: Keep vendor research autonomous; gate applications/contact.

### Client Portal (client_portal) — opportunity_lab
- Level 1 (autonomous): internal portal content drafts, internal reports
- Level 2 (approval-gated): client-facing portal publishing, client notification
- Level 3 (blocked): client data exposure externally, external AI on customer data
- next: Keep portal drafts autonomous; gate client-facing publishing.

### Admin / Tenants / Users (admin_tenants_users) — ops_improvements
- Level 1 (autonomous): internal admin reporting (read-only)
- Level 2 (approval-gated): tenant/user configuration change proposal
- Level 3 (blocked): tenant isolation bypass, destructive admin actions, credential changes
- next: Keep admin reporting autonomous; gate config changes; block isolation bypass.

### Monitoring / Health (monitoring_health) — ops_improvements
- Level 1 (autonomous): health checks, internal status reports, proof events
- Level 2 (approval-gated): —
- Level 3 (blocked): destructive remediation without approval
- next: Keep monitoring autonomous; gate any destructive remediation.

