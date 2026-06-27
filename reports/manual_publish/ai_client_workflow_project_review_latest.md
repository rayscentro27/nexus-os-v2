# AI Access + Client Workflow Project Review (Pre-Build Audit)

- generated_at: 2026-06-27T00:28:00.037214+00:00
- ok: True
- automation_control_center_complete: True
- client_workflow_engine_present: True

## Summary
Automation Control Center complete=True. Client Workflow Engine present=True. This task adds the AI Department Access Controls + Client Vault CONTRACT (mock adapter only) in front of the existing engine. No real vault, no 2nd Supabase, no real client data, no CRM integration.

## 2. Reuse
- task_requests + approvals + Ray Review Queue (rayReviewQueuePolicy.ts, build_ray_review_queue.py) for gating.
- nexus_events proof ledger; scripts/research/common.py write_report + scripts/social/_supabase.py conventions.
- Automation levels/guards (nexusAutomationLevels/Policy/Matrix/HighRiskGuards) — classify every AI action.
- Client workflow engine (clientWorkflow*.ts, clientWorkflowHermes.ts) already built in commit c75ffc0.
- MissionControl ClientWorkflowCard for Command Center visibility.
- scripts/compliance/classify_claim_risk.py for client-facing text gating.

## 4. Approval / Ray Review patterns
- rayReviewQueuePolicy.ts classification + decision reasons (incl. blocked_high_risk_escalation).
- nexusActionPolicy.ts getAutomationApprovalDisposition / shouldCreateApprovalRow / isBlockedFromDirectApproval.

## 5. Hermes / Command Center patterns
- MissionControl chiprow + card pattern; buildHermesWorkflowDigest for sanitized aggregate counts.
- nexusResearchReports.ts + report reader for report visibility.

## 6. Affiliate / revenue patterns
- partner_offers + client_recommendations tables; affiliateOpportunityTypes/Tracker.
- clientWorkflowAffiliate.ts (partner vs DIY map); goclearRevenueHub revenue scoring.

## 7. To add
- AI department roles + per-agent access policy + client data sensitivity policy + access-policy lib.
- Hermes no-raw-client-data redaction policy + sanitized client signals model.
- Credit Specialist Supabase-only access contract + Researcher AI no-PII contract.
- Client Vault CONTRACT + mock/dev adapter only (no live connection, no 2nd Supabase, no real data).
- Approved knowledge model; audit logging contract (mock events only).
- ai_access + client_vault verification/report scripts; Command Center AI access/vault status; CRM-eval-later doc.

## 8. Do not duplicate
- Do NOT rebuild the client workflow engine — reuse commit c75ffc0.
- Do NOT rebuild approvals/Ray Review/automation levels — reuse.
- Do NOT add a real Client Vault / 2nd Supabase / real client data — mock adapter only.
- Do NOT integrate any CRM repo (Twenty/Relaticle/Atomic/Open Mercato/NextCRM/crm-logic).

## 9. Migrations needed
None required for v1. Client Vault is contract + mock adapter only; durable client tables (0012) already exist for the local engine. No second Supabase project.

## 10. Plan
- 1. AI department roles + access policy + sensitivity policy + lib (Parts 2-5).
- 2. Hermes redaction + sanitized signals (Parts 3, 8).
- 3. Client Vault contract + mock adapter + data model + audit contract (Parts 6, 7, 12).
- 4. Approved knowledge model + access views + blocked-access rules (Parts 9, 10, 11).
- 5. ai_access + client_vault scripts (Part 11/23) reusing report conventions.
- 6. Command Center AI access/vault status + CRM-eval doc (Parts 22, 25).
- 7. Verify (build/watch/all dry-runs) then commit (Part 24).

