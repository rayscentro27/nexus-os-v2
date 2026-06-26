# Nexus Automation Category Matrix

Generated from `src/config/nexusAutomationCategoryMatrix.ts` / `scripts/automation/automation_model.py`.
Automation is classified category-by-category. See [NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md).

Total categories: 30

## Research / Source Intake (`research_source_intake`)
- **Owner department:** source_intake
- **Level 1 (autonomous internal):** source intake enrichment, scoring, routing, internal cards, internal reports
- **Level 2 (approval-gated):** connector activation for live source pulls, scheduler activation
- **Level 3 (blocked / high-risk):** broad scraping, external AI on sensitive/private/customer data
- **Risk notes:** Internal research is safe; broad scraping and sensitive external AI are blocked.
- **Next recommended action:** Keep enrichment/scoring autonomous; leave live connectors and scheduler as approval-gated.

## YouTube Research (`youtube_research`)
- **Owner department:** source_intake
- **Level 1 (autonomous internal):** metadata check (placeholder/fallback), transcript review from local samples, scoring/routing, internal reports, Hermes prep brief
- **Level 2 (approval-gated):** metadata connector activation, scheduler activation, publish of derived content
- **Level 3 (blocked / high-risk):** YouTube media downloads, broad scraping
- **Risk notes:** Metadata-only is safe; media downloads are blocked. Connector is currently not_configured.
- **Next recommended action:** Run metadata/transcript dry-runs; keep connector + scheduler approval-gated.

## SEO / Marketing (`seo_marketing`)
- **Owner department:** growth
- **Level 1 (autonomous internal):** SEO keyword scoring, opportunity scoring, internal cards/reports
- **Level 2 (approval-gated):** publishing to site, site/production change, scheduler activation
- **Level 3 (blocked / high-risk):** production deploy of site changes, external AI on sensitive data
- **Risk notes:** Scoring is internal; publishing/site changes leave the building.
- **Next recommended action:** Keep keyword scoring autonomous; gate any publish/site change.

## Affiliate Marketing (`affiliate_marketing`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** affiliate opportunity scoring, partner research, internal cards/reports
- **Level 2 (approval-gated):** publishing affiliate content, outbound partner contact
- **Level 3 (blocked / high-risk):** spend/commitment actions, broad scraping of partner sites
- **Risk notes:** Scoring is internal; outbound partner contact and publishing are gated.
- **Next recommended action:** Keep opportunity scoring autonomous; gate outbound/publish.

## Content Opportunity Lab (`content_opportunity_lab`)
- **Owner department:** growth
- **Level 1 (autonomous internal):** content opportunity scoring, experiment cards, internal reports
- **Level 2 (approval-gated):** publishing content, sending content, scheduler activation
- **Level 3 (blocked / high-risk):** external AI on sensitive/customer data
- **Risk notes:** Idea/experiment work is internal; publishing/sending are gated.
- **Next recommended action:** Keep experiment cards autonomous; gate publish/send.

## Creative Studio (`creative_studio`)
- **Owner department:** creative_studio
- **Level 1 (autonomous internal):** draft creative generation, internal review cards, internal reports
- **Level 2 (approval-gated):** publishing creative, sending creative to clients, ad creative activation
- **Level 3 (blocked / high-risk):** external AI on sensitive/customer data, spend on paid creative tools
- **Risk notes:** Drafts are internal until publish/send; then gated.
- **Next recommended action:** Keep drafting autonomous; gate publish/send/client delivery.

## Design Library (`design_library`)
- **Owner department:** design_library
- **Level 1 (autonomous internal):** design library organization, tagging, internal cards/reports
- **Level 2 (approval-gated):** publishing assets externally, client delivery
- **Level 3 (blocked / high-risk):** external AI on sensitive/customer data
- **Risk notes:** Organization is internal; external delivery is gated.
- **Next recommended action:** Keep organizer autonomous; gate external delivery.

## GoClear Revenue Hub (`goclear_revenue_hub`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** internal revenue metric cards, internal reports, scoring
- **Level 2 (approval-gated):** lead contact, payment-link creation, campaign publishing, scheduler activation
- **Level 3 (blocked / high-risk):** payment/spend actions, destructive DB writes
- **Risk notes:** Internal cards are safe; lead contact and payment links leave the building.
- **Next recommended action:** Keep revenue cards autonomous; gate lead contact and payment links.

## GoClear / Apex Client Intake (`goclear_apex_client_intake`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** lead scoring, readiness checklist, internal cards/reports
- **Level 2 (approval-gated):** client notification, client contact, client-facing scheduling
- **Level 3 (blocked / high-risk):** client data exposure externally, external AI on customer data
- **Risk notes:** Scoring/checklists are internal; client contact is gated; client data exposure is blocked.
- **Next recommended action:** Keep scoring/checklists autonomous; gate client contact.

## Credit Repair / Funding Guidance (`credit_repair_funding_guidance`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** internal guidance research, scoring, internal reports
- **Level 2 (approval-gated):** client-facing guidance delivery, client contact
- **Level 3 (blocked / high-risk):** compliance-sensitive claims published without review, external AI on credit-sensitive data
- **Risk notes:** High compliance risk. Research internal; client delivery gated; sensitive external AI blocked.
- **Next recommended action:** Keep research autonomous; gate all client-facing delivery; compliance review required.

## Opportunity Lab (`opportunity_lab`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** opportunity research, scoring, routing, internal cards/reports
- **Level 2 (approval-gated):** outbound contact, publishing, scheduler activation
- **Level 3 (blocked / high-risk):** broad scraping, external AI on sensitive data
- **Risk notes:** Research is internal; outbound/publish gated; broad scraping blocked.
- **Next recommended action:** Keep opportunity research autonomous; gate outbound/publish.

## Agent Jobs (`agent_jobs`)
- **Owner department:** agent_jobs
- **Level 1 (autonomous internal):** job status reporting, internal cards, internal reports
- **Level 2 (approval-gated):** scheduler activation, enabling persistent jobs
- **Level 3 (blocked / high-risk):** raw auto_executor exposure, destructive job actions
- **Risk notes:** Status is internal; persistent jobs gated; raw auto_executor blocked.
- **Next recommended action:** Keep status feeder autonomous; gate scheduler/persistent jobs.

## Integrations (`integrations`)
- **Owner department:** integrations
- **Level 1 (autonomous internal):** integration status reporting, internal cards/reports
- **Level 2 (approval-gated):** connector activation, OAuth setup, credential connection
- **Level 3 (blocked / high-risk):** credential changes without review, connecting sensitive systems, secret printing
- **Risk notes:** Status is internal; connector activation gated; credential changes blocked.
- **Next recommended action:** Keep status feeder autonomous; gate connector activation.

## Events Feed / Proof Ledger (`events_feed_proof_ledger`)
- **Owner department:** events_feed
- **Level 1 (autonomous internal):** internal proof events, internal reports, ledger reads
- **Level 2 (approval-gated):** —
- **Level 3 (blocked / high-risk):** destructive ledger writes, tampering with proof history
- **Risk notes:** Proof logging is internal and append-only; destructive ledger writes are blocked.
- **Next recommended action:** Keep proof logging autonomous; never allow destructive ledger writes.

## Approvals (`approvals`)
- **Owner department:** approvals
- **Level 1 (autonomous internal):** approvals reporting (read-only), internal decision briefs
- **Level 2 (approval-gated):** Ray decision execution of an approved item
- **Level 3 (blocked / high-risk):** auto-approving high-risk items, bypassing approval gates
- **Risk notes:** Reporting is internal; the Ray decision itself is gated; auto-approval blocked.
- **Next recommended action:** Keep approvals reporting autonomous; require Ray for each decision.

## Ray Review Queue (`ray_review_queue`)
- **Owner department:** command_center
- **Level 1 (autonomous internal):** queue building from true decisions, internal reports
- **Level 2 (approval-gated):** marking an item approved/executed
- **Level 3 (blocked / high-risk):** auto-executing queued items
- **Risk notes:** Building the queue is internal; execution requires Ray; auto-execute blocked.
- **Next recommended action:** Keep queue builder autonomous; never auto-execute queued items.

## Hermes / Jarvis (`hermes_jarvis`)
- **Owner department:** command_center
- **Level 1 (autonomous internal):** internal recommendations, prep briefs, summaries, internal reports
- **Level 2 (approval-gated):** Mac/computer-control bridge activation, outbound actions on Ray behalf
- **Level 3 (blocked / high-risk):** raw command execution from browser, external AI on sensitive data
- **Risk notes:** Recommendations are internal; bridge/outbound gated; raw command execution blocked.
- **Next recommended action:** Keep Hermes recommendations autonomous; gate any bridge/outbound execution.

## Trading Lab (`trading_lab`)
- **Owner department:** trading_lab
- **Level 1 (autonomous internal):** paper-only strategy research, backtest imports (local), scoring, internal reports
- **Level 2 (approval-gated):** —
- **Level 3 (blocked / high-risk):** live trading, broker execution, funded account actions, raw auto_executor exposure
- **Risk notes:** Paper-only research is internal. Live trading/broker/funded actions are BLOCKED Level 3.
- **Next recommended action:** Keep paper-only research autonomous; live execution stays blocked under its own contract.

## Scheduler / Automation (`scheduler_automation`)
- **Owner department:** ops_improvements
- **Level 1 (autonomous internal):** scheduler candidate proposals (proposal-only), internal reports
- **Level 2 (approval-gated):** scheduler activation, enabling persistent automation
- **Level 3 (blocked / high-risk):** cron/launchd/systemd creation without approval
- **Risk notes:** Proposals are internal; activation is gated; unapproved persistent jobs blocked.
- **Next recommended action:** Generate candidates only; never activate a scheduler without Ray approval.

## Production / Deployment (`production_deployment`)
- **Owner department:** ops_improvements
- **Level 1 (autonomous internal):** deploy readiness reports (internal)
- **Level 2 (approval-gated):** production change proposal
- **Level 3 (blocked / high-risk):** production deploys, destructive production actions
- **Risk notes:** Readiness reporting internal; production deploys blocked unless separately approved.
- **Next recommended action:** Keep readiness reporting autonomous; deploys stay blocked/gated.

## Email / SMS / DM / Social (`email_sms_dm_social`)
- **Owner department:** growth
- **Level 1 (autonomous internal):** draft messages, internal review cards
- **Level 2 (approval-gated):** sending email/SMS/DM, social posting, campaign publishing
- **Level 3 (blocked / high-risk):** bulk send, spam automation
- **Risk notes:** Drafts internal; sending is gated; bulk/spam send blocked.
- **Next recommended action:** Keep drafting autonomous; gate every send; block bulk/spam.

## Ads / Spend (`ads_spend`)
- **Owner department:** growth
- **Level 1 (autonomous internal):** ad opportunity research, internal cards/reports
- **Level 2 (approval-gated):** ad campaign activation proposal
- **Level 3 (blocked / high-risk):** ad spend activation, payment charges
- **Risk notes:** Research internal; spend blocked. No money leaves without separate approval.
- **Next recommended action:** Keep ad research autonomous; spend stays blocked/gated.

## Database / Supabase (`database_supabase`)
- **Owner department:** ops_improvements
- **Level 1 (autonomous internal):** read-only queries, internal schema reports
- **Level 2 (approval-gated):** schema change proposal
- **Level 3 (blocked / high-risk):** destructive DB writes, RLS weakening, tenant isolation bypass
- **Risk notes:** Reads internal; destructive writes / RLS weakening blocked.
- **Next recommended action:** Keep reads autonomous; block destructive DB and RLS changes.

## Files / Reports / Imports (`files_reports_imports`)
- **Owner department:** ops_improvements
- **Level 1 (autonomous internal):** local report generation, safe local imports, internal cards
- **Level 2 (approval-gated):** —
- **Level 3 (blocked / high-risk):** committing .env/secrets, broad scraping into imports
- **Risk notes:** Local reports/imports internal; secret commits and broad-scrape imports blocked.
- **Next recommended action:** Keep local report generation autonomous; never commit secrets.

## NotebookLM / Research Library (`notebooklm_research_library`)
- **Owner department:** source_intake
- **Level 1 (autonomous internal):** library organization, internal summaries, internal reports
- **Level 2 (approval-gated):** connector activation
- **Level 3 (blocked / high-risk):** external AI on sensitive/customer data
- **Risk notes:** Library organization internal; connector gated; sensitive external AI blocked.
- **Next recommended action:** Keep library organization autonomous; gate connector activation.

## Grants / Funding Opportunities (`grants_funding_opportunities`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** grant opportunity research, scoring, internal cards/reports
- **Level 2 (approval-gated):** application submission, outbound contact
- **Level 3 (blocked / high-risk):** spend/commitment actions
- **Risk notes:** Research internal; submissions/outbound gated.
- **Next recommended action:** Keep grant research autonomous; gate submissions/outbound.

## Business Credit / Vendor Accounts (`business_credit_vendor_accounts`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** vendor research, scoring, internal cards/reports
- **Level 2 (approval-gated):** account application, outbound vendor contact
- **Level 3 (blocked / high-risk):** credential changes, spend/commitment actions
- **Risk notes:** Research internal; applications/contact gated; credential changes blocked.
- **Next recommended action:** Keep vendor research autonomous; gate applications/contact.

## Client Portal (`client_portal`)
- **Owner department:** opportunity_lab
- **Level 1 (autonomous internal):** internal portal content drafts, internal reports
- **Level 2 (approval-gated):** client-facing portal publishing, client notification
- **Level 3 (blocked / high-risk):** client data exposure externally, external AI on customer data
- **Risk notes:** Drafts internal; client-facing publishing gated; client data exposure blocked.
- **Next recommended action:** Keep portal drafts autonomous; gate client-facing publishing.

## Admin / Tenants / Users (`admin_tenants_users`)
- **Owner department:** ops_improvements
- **Level 1 (autonomous internal):** internal admin reporting (read-only)
- **Level 2 (approval-gated):** tenant/user configuration change proposal
- **Level 3 (blocked / high-risk):** tenant isolation bypass, destructive admin actions, credential changes
- **Risk notes:** Reporting internal; config changes gated; isolation bypass blocked.
- **Next recommended action:** Keep admin reporting autonomous; gate config changes; block isolation bypass.

## Monitoring / Health (`monitoring_health`)
- **Owner department:** ops_improvements
- **Level 1 (autonomous internal):** health checks, internal status reports, proof events
- **Level 2 (approval-gated):** —
- **Level 3 (blocked / high-risk):** destructive remediation without approval
- **Risk notes:** Monitoring is internal; destructive auto-remediation blocked.
- **Next recommended action:** Keep monitoring autonomous; gate any destructive remediation.

