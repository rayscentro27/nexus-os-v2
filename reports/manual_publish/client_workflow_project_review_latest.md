# Client Workflow Project Review (Pre-Build Audit)

- generated_at: 2026-06-27T00:04:14.847535+00:00
- ok: True

## Summary
Audit complete. Strong reusable foundation exists (task_requests, approvals/Ray Review Queue, partner_offers/client_recommendations, nexus_events, automation levels, compliance classifier, report conventions). The durable client-domain tables and the workflow/scoring/letters/mailing/reminder/Hermes engines are missing and will be added additively without duplicating existing systems.

## 1. Reusable (do not rebuild)
- **task_requests table + lib/taskRequests.ts** — Universal Ray-approved card system with sensitivity labels (credit_sensitive, funding_sensitive) and admin-only RLS. Use for workflow tasks, reminders, and recommendation cards.
- **approvals table + Ray Review Queue (rayReviewQueuePolicy.ts, scripts/review/build_ray_review_queue.py)** — Approval gating + one decision card per ready plan. Reuse instead of a new approval system.
- **partner_offers + client_recommendations tables** — Affiliate offers + per-client recommendations already modeled. Reuse for affiliate recommendation engine.
- **affiliateOpportunityTypes.ts / affiliateOpportunityTracker.ts** — Affiliate categories + scoring model already present; extend, do not duplicate.
- **nexus_events (proof ledger)** — Append-only proof events for every internal write. Reuse for workflow proof.
- **nexusActionPolicy.ts + automation levels (nexusAutomationLevels/Policy/Matrix/HighRiskGuards)** — Level 1/2/3 classification + guards already exist. Classify every client-workflow action through these.
- **scripts/compliance/classify_claim_risk.py** — Deterministic compliance classifier for credit/funding text. Reuse before any client-facing recommendation.
- **goclearRevenueHub.ts + goclearRevenueMetrics.ts** — Revenue potential scoring for upsell/affiliate opportunity scoring.
- **scripts/research/common.py write_report + scripts/social/_supabase.py** — Report JSON+MD writer and Supabase helpers (configured()/get/insert/q). Reuse conventions; scripts stay dry-run safe without DB.
- **MissionControl.tsx + nexusDepartmentFeeders.ts** — Command Center cards + feeder registry. Add a Client Workflow card; do not redesign UI.
- **workspaces (tenant) + admin_users (RLS gate)** — Tenant + admin RLS pattern. New tables reuse this exact RLS pattern.

## 2. Partial — extend
- **GoClear / Apex tab (nexusTabs.ts)** — Exists as 'partial_connected' funding-readiness workspace using partner_offers/client_recommendations/task_requests. Extend with client workflow stages, credit/business scoring, letters, mailing, reminders.
- **client_recommendations table** — Has client_label/title/recommendation_type/partner_offer_id. Extend usage for affiliate vs DIY path tracking via metadata; no schema change required for v1.
- **Affiliate model** — AffiliateOpportunity is for monetization research, not per-client setup recommendations. Add a client-workflow affiliate recommendation layer that maps setup items -> partner/DIY options.

## 3. Missing
- Client workflow status engine (signup -> funding-ready stages, days_stuck, progress %).
- Credit report source selection (SmartCredit recommended vs AnnualCreditReport.com free vs manual upload).
- SmartCredit connector shell (affiliate-link/partner statuses, NO password/scrape/login).
- Credit score history model + manual score entry.
- Credit analysis engine (utilization, negatives, blockers, readiness scores).
- Business setup engine (LLC/EIN/agent/address/phone/web/DUNS/bank/vendor) with partner vs DIY paths.
- Business bankability + funding readiness scoring.
- Credit repair letter packet + DocuPost/USPS mailing workflow (approval-gated, no auto-mail).
- Client progress reminder / stuck-client engine.
- Hermes client workflow recommendation layer (proactive, internal-only).
- Client workflow Python report generators + policy verification.
- Durable client-domain tables migration (client_profiles, score history, business setup, letters, mailings, reminders).

## 4. Do not duplicate
- Do NOT build a new approval system — reuse approvals + Ray Review Queue.
- Do NOT build a new task/card table — reuse task_requests with new task_type values.
- Do NOT build a new affiliate table — reuse partner_offers + client_recommendations.
- Do NOT build a new proof system — reuse nexus_events.
- Do NOT build a new automation policy — reuse nexusActionPolicy + automation levels/guards.
- Do NOT build a new report writer — reuse scripts/research/common.py write_report.

## 5. Files to update
- src/components/command-center/MissionControl.tsx (add Client Workflow card).
- src/config/nexusDepartmentFeeders.ts (register client workflow feeders + automation levels).
- docs/operations/NEXUS_CLIENT_INTAKE_AUTOMATION_POLICY.md (cross-reference client workflow engine).

## 5. Files to create
- src/config/clientWorkflow.ts, src/config/clientWorkflowReminders.ts, src/config/clientWorkflowAffiliate.ts
- src/lib/clientWorkflowEngine.ts, src/lib/clientWorkflowHermes.ts
- supabase/migrations/0012_client_workflow_engine.sql
- scripts/client_workflow/* (model + 6 generators/verifier)
- docs/operations/NEXUS_CLIENT_WORKFLOW_ENGINE.md

## 6. Tables supporting this workflow
- task_requests (cards/tasks/reminders/recommendations)
- approvals (approval gating)
- nexus_events (proof ledger)
- partner_offers + client_recommendations (affiliate)
- workspaces (tenant) + admin_users (RLS)

## 7. Migrations needed
- 0012_client_workflow_engine.sql — additive, admin-only RLS (reusing existing pattern), sensitivity-labeled: client_profiles, client_workflow_stage_history, credit_score_history, business_setup_items, credit_letter_packets, client_mailings, client_reminders.

## 8. Approval / Ray Review patterns to reuse
- Reuse rayReviewQueuePolicy.ts classification + build_ray_review_queue.py builder.
- One Ray Review card per READY plan (credit action plan / business action plan / client-facing plan), never per negative item.
- Level 2 (approval-gated): sends, client contact, mailing, dispute submission, funding applications, connector/scheduler activation.
- Level 3 (blocked): SmartCredit password storage/scrape/login, auto-mail, auto-file LLC/EIN, auto-open accounts, auto-apply funding, external AI on client credit data.

## 9. Command Center / Hermes patterns to reuse
- Reuse MissionControl chiprow + ExecutiveOfficePanel card pattern (counts + notes).
- Reuse Hermes prep-brief/recommendation report pattern (nexusResearchReports.ts + report reader).
- Reuse nexusDepartmentFeeders automation-level registry for client workflow feeders.

## 10. Part 2 implementation plan
- 1. TS models: clientWorkflow.ts (stages, sources, connector statuses, score model, business setup items, letter/mailing types), clientWorkflowReminders.ts (templates/timings), clientWorkflowAffiliate.ts (categories + partner/DIY map).
- 2. TS engines: clientWorkflowEngine.ts (status/progress/days_stuck/scoring) + clientWorkflowHermes.ts (proactive recommendations).
- 3. Migration 0012 (durable tables, admin RLS, sensitivity labels).
- 4. Python: client_workflow_model.py (shared) + 6 dry-run generators/verifier with deterministic sample data.
- 5. Command Center card + feeder registration + docs.
- 6. Verify (build/watch/dry-runs) then commit.

