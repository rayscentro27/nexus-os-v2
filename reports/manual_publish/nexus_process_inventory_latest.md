# Nexus Process Inventory

- timestamp: 2026-06-27T01:53:09.333806+00:00
- status: ok
- dry_run: True
- external_action: false · money_spent: false · level_3_blocked: true

## By status
- ready_to_run: 28
- needs_data: 1
- needs_config: 1
- manual_only: 1
- blocked_by_policy: 1
- approval_required: 1

## Processes
- [ready_to_run] Automation Control Center (automation) — scripts/automation/generate_automation_control_report.py
- [ready_to_run] Automation policy verification (automation) — scripts/automation/verify_automation_policy.py
- [ready_to_run] High-risk guard verification (automation) — scripts/automation/verify_high_risk_guards.py
- [ready_to_run] Scheduler approval candidates (automation) — scripts/automation/generate_scheduler_approval_candidates.py
- [ready_to_run] AI department access verification (ai_access) — scripts/ai_access/verify_ai_department_access.py
- [ready_to_run] AI agent runtime verification (ai_access) — scripts/ai_access/verify_agent_runtime.py
- [ready_to_run] AI access report (ai_access) — scripts/ai_access/generate_ai_access_report.py
- [ready_to_run] Credit Specialist contract report (ai_access) — scripts/ai_access/generate_credit_specialist_contract_report.py
- [ready_to_run] Hermes redaction report (ai_access) — scripts/ai_access/generate_hermes_redaction_report.py
- [ready_to_run] Client Vault contract report (client_vault) — scripts/client_vault/generate_client_vault_contract_report.py
- [ready_to_run] Client Vault contract verification (client_vault) — scripts/client_vault/verify_client_vault_contract.py
- [ready_to_run] Client workflow engine report (client_workflow) — scripts/client_workflow/generate_client_workflow_report.py
- [ready_to_run] Affiliate recommendation report (client_workflow) — scripts/client_workflow/generate_affiliate_recommendation_report.py
- [ready_to_run] Stuck-client report (client_workflow) — scripts/client_workflow/generate_stuck_client_report.py
- [ready_to_run] Hermes client recommendations (client_workflow) — scripts/client_workflow/generate_hermes_client_recommendations.py
- [ready_to_run] Client workflow policy verification (client_workflow) — scripts/client_workflow/verify_client_workflow_policy.py
- [ready_to_run] SmartCredit/AnnualCreditReport source flow (client_workflow) — config: clientWorkflow.ts
- [ready_to_run] Credit score/report analysis flow (client_workflow) — lib: clientWorkflowEngine.ts
- [ready_to_run] Business setup workflow (client_workflow) — config: clientWorkflow.ts
- [ready_to_run] DocuPost/USPS mailing workflow (client_workflow) — config: clientWorkflow.ts
- [ready_to_run] Reminders/stuck-client engine (client_workflow) — config: clientWorkflowReminders.ts
- [ready_to_run] GoClear subscription market research (monetization) — scripts/night_run/generate_goclear_subscription_market_research.py
- [ready_to_run] Online business bank affiliate research (monetization) — scripts/night_run/generate_online_business_bank_affiliate_research.py
- [ready_to_run] Four revenue streams (monetization) — scripts/night_run/generate_revenue_streams.py
- [ready_to_run] Client workflow monetization (monetization) — scripts/night_run/generate_client_workflow_monetization.py
- [ready_to_run] Hermes executive brief (hermes) — scripts/night_run/generate_hermes_executive_brief.py
- [needs_data] SEO/affiliate scoring (growth) — lib: seoKeywordScout.ts / affiliateOpportunityTracker.ts
- [needs_config] YouTube research foundation (research) — config: youtubeChannelWatchlist.ts (API not configured by design)
- [manual_only] Trading paper-only research (trading) — scripts/trading/*
- [ready_to_run] Approvals / Ray Review Queue (approvals) — scripts/review/build_ray_review_queue.py
- [ready_to_run] Command Center / System Health (system) — npm run nexus:watch
- [blocked_by_policy] Live Client Vault connection (client_vault) — blocked: not_connected_by_design
- [approval_required] Sending/mailing/charging/contacting (execution) — blocked until Ray approval
