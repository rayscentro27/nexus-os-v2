# Credit Specialist Supabase-Only Contract

- ok: True

## Proofs
- supabase_only_no_web_tools: True
- approved_knowledge_only: True
- vault_mock_only: True
- client_facing_approval_gated: True
- no_external_ai_on_client_data: True

## May use
- approved_credit_knowledge
- approved_dispute_rules
- approved_funding_readiness_rules
- approved_compliance_language
- mock_client_credit_report_via_vault_adapter
- mock_client_business_setup_via_vault_adapter
- client_workflow_tasks_via_adapter
- client_action_plan_drafts

## Must NOT use
- internet
- web_browsing
- youtube
- unapproved_research
- external_ai_on_client_data
- raw_client_vault_production_connection
- production_smartcredit_files
