# Nexus Night-Run Readiness

- timestamp: 2026-06-27T01:53:11.106870+00:00
- status: ok
- dry_run: True
- external_action: false · money_spent: false · level_3_blocked: true

## Ran OK (28/28)
- scripts/automation/generate_automation_control_report.py
- scripts/automation/verify_automation_policy.py
- scripts/automation/verify_high_risk_guards.py
- scripts/automation/generate_scheduler_approval_candidates.py
- scripts/ai_access/verify_ai_department_access.py
- scripts/ai_access/verify_agent_runtime.py
- scripts/ai_access/generate_ai_access_report.py
- scripts/ai_access/generate_credit_specialist_contract_report.py
- scripts/ai_access/generate_hermes_redaction_report.py
- scripts/client_vault/generate_client_vault_contract_report.py
- scripts/client_vault/verify_client_vault_contract.py
- scripts/client_workflow/generate_client_workflow_report.py
- scripts/client_workflow/generate_affiliate_recommendation_report.py
- scripts/client_workflow/generate_stuck_client_report.py
- scripts/client_workflow/generate_hermes_client_recommendations.py
- scripts/client_workflow/verify_client_workflow_policy.py
- scripts/night_run/generate_night_run_project_review.py
- scripts/night_run/generate_process_inventory.py
- scripts/night_run/generate_automation_night_readiness.py
- scripts/night_run/generate_hermes_executive_brief.py
- scripts/night_run/generate_goclear_subscription_market_research.py
- scripts/night_run/generate_online_business_bank_affiliate_research.py
- scripts/night_run/generate_revenue_streams.py
- scripts/night_run/generate_client_workflow_monetization.py
- scripts/night_run/generate_business_setup_banking_monetization.py
- scripts/night_run/generate_docupost_usps_mailing_monetization.py
- scripts/night_run/generate_client_reminder_revenue_risk.py
- scripts/night_run/generate_approval_and_blocked.py

## Blocked by policy
- Live Client Vault connection

## Needs approval
- Sending/mailing/charging/contacting

## What should happen next
- Validate GoClear subscription pricing; confirm online-bank affiliate primary.
- Review Ray Review Queue items; approve plans before client exposure.
- Keep schedulers/connectors off until approved.
