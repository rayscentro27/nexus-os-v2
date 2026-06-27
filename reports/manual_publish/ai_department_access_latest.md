# AI Department Access Report

- generated_at: 2026-06-27T01:53:06.958947+00:00
- ok: True

## Roles
### hermes_ceo_advisor
- internet: True · vault: False · approved-knowledge-only: False · client-facing: approval_gated
- allowed: approved_knowledge, internet, sanitized_client_signals, supabase_system_reports, web_browse
- blocked: client_vault_adapter, external_ai_api

### researcher_ai
- internet: True · vault: False · approved-knowledge-only: False · client-facing: blocked
- allowed: approved_knowledge, internet, supabase_system_reports, web_browse, youtube
- blocked: client_vault_adapter, sanitized_client_signals

### credit_specialist_ai
- internet: False · vault: True · approved-knowledge-only: True · client-facing: approval_gated
- allowed: approved_knowledge, client_vault_adapter, sanitized_client_signals, supabase_system_reports
- blocked: external_ai_api, internet, unapproved_research, web_browse, youtube

### funding_specialist_ai
- internet: False · vault: True · approved-knowledge-only: True · client-facing: approval_gated
- allowed: approved_knowledge, client_vault_adapter, sanitized_client_signals, supabase_system_reports
- blocked: external_ai_api, internet, unapproved_research, web_browse, youtube

### business_setup_specialist_ai
- internet: False · vault: True · approved-knowledge-only: True · client-facing: approval_gated
- allowed: approved_knowledge, client_vault_adapter, sanitized_client_signals, supabase_system_reports
- blocked: external_ai_api, internet, unapproved_research, web_browse, youtube

### client_chat_ai
- internet: False · vault: True · approved-knowledge-only: True · client-facing: approval_gated
- allowed: approved_knowledge, client_vault_adapter
- blocked: external_ai_api, internet, supabase_system_reports, unapproved_research, web_browse, youtube

