# Hermes Capability Certification Matrix

## Certified Read Capabilities

| Capability | Version | Semantic Def | Lifecycle | Owner | Handler | Source | Tenant | Auth | Side Effect | Tests | Production |
|-----------|---------|-------------|-----------|-------|---------|--------|--------|------|-------------|-------|------------|
| get_client_count | v2 | production_client_summary@v1 | certified_read | Ray | hermes._get_client_count | Supabase client_profiles | goclear | admin | read | pass | yes |
| get_system_status | v1 | current_running_process_summary@v1 | certified_read | Ray | hermes._get_system_status | nexus_process_registry.json | global | admin | read | pass | yes |
| get_failure_report | v1 | current_failure_summary@v1 | certified_read | Ray | hermes._get_failure_report | heartbeat_latest.json | global | admin | read | pass | yes |
| get_alpha_status | v1 | current_alpha_status@v1 | certified_read | Ray | hermes._get_alpha_status | alpha_telegram_status.json | global | admin | read | pass | yes |
| client_acquisition_advisory | v1 | (none) | certified_read | Ray | static response | internal | global | admin | none | pass | yes |
| create_opencode_prompt | v1 | (none) | certified_read | Ray | hermes._create_opencode_prompt | internal context | global | admin | none | pass | yes |
| process_status | v1 | process_definition_summary@v1 | certified_read | Ray | hermes._get_process_status | Supabase nexus_process_definitions,nexus_process_runs | server_injected | admin | read | pass | yes |
| process_failures | v1 | process_failure_summary@v1 | certified_read | Ray | hermes._get_process_failures | Supabase nexus_process_runs | server_injected | admin | read | pass | yes |
| research_history | v1 | research_run_summary@v1 | certified_read | Ray | hermes._get_research_history | Supabase nexus_research_runs,nexus_research_results | server_injected | admin | read | pass | yes |
| opportunities | v1 | business_opportunity_summary@v1 | certified_read | Ray | hermes._get_opportunities | Supabase business_opportunities | server_injected | admin | read | pass | yes |
| trading_status | v1 | current_trading_status@v1 | certified_read | Ray | hermes._get_trading_status | oanda_practice_engine_status_latest.json | global | admin | read | pass | yes |
| pending_approvals | v1 | pending_approval_summary@v1 | certified_read | Ray | hermes._get_pending_approvals | ray_review_queue_latest.json | global | admin | read | pass | yes |

## Certified Action Capabilities

| Capability | Version | Semantic Def | Lifecycle | Owner | Handler | Source | Tenant | Auth | Side Effect | Confirmation | Idempotency | Tests | Production |
|-----------|---------|-------------|-----------|-------|---------|--------|--------|------|-------------|--------------|-------------|-------|------------|
| send_approved_email | v1 | (none) | certified_action | Ray | actions.send_approved_email | resend_api | goclear | admin | external | required | mission_id_based | pass | yes |
| schedule_report | v1 | (none) | certified_action | Ray | actions.schedule_report | temporal_adapter | goclear | admin | write | required | mission_id_based | pass | yes |
| create_work_order | v1 | (none) | certified_action | Ray | actions.create_work_order | supabase_table:task_requests | goclear | admin | write | required | mission_id_based | pass | yes |

## Certification Summary

- **Certified read**: 12 capabilities
- **Certified action**: 3 capabilities
- **Quarantined**: 0 capabilities
- **Draft**: 0 capabilities
- **Deprecated**: 0 capabilities
- **Disabled**: 0 capabilities

## Action Capability Details

### send_approved_email_v1

**Required fields**: recipient, subject, body
**Optional fields**: reply_to, template_id, related_mission
**Flow**: TaskSpec → dispatcher → validate fields → idempotency check → Resend Edge Function → receipt → trace
**Idempotency**: mission_id based, stored in action_receipts/
**Provider**: Resend via Supabase Edge Function
**Receipt**: provider_request_id, recipient_domain, subject_hash
**Redaction**: No email body in trace, recipient domain only

### schedule_report_v1

**Required fields**: report_definition, execution_time
**Optional fields**: timezone (default America/Phoenix), recurrence, delivery_channel, report_format
**Flow**: TaskSpec → dispatcher → validate fields → idempotency check → store schedule → worker picks up → execute read capability → format → Telegram delivery
**Idempotency**: mission_id based, stored in action_receipts/
**Durability**: File-based schedule storage (Temporal adapter when enabled)
**Receipt**: schedule_id, execution_time, report_definition

### create_work_order_v1

**Required fields**: title, description, source_context
**Optional fields**: owner, priority, due_date, linked_opportunity, linked_research, assigned_agent
**Flow**: TaskSpec → dispatcher → validate fields → idempotency check → Supabase insert → receipt → trace
**Idempotency**: mission_id based, stored in action_receipts/
**Storage**: Supabase task_requests table
**Receipt**: work_order_id, record_id, title, status

## Legacy Paths (Retired)

The following legacy paths are no longer production-reachable:

1. `send_email` (quarantined capability ID) → replaced by `send_approved_email`
2. `create_work_order` (quarantined capability ID) → replaced by `create_work_order` (certified)
3. Legacy bridge tool handlers → not routed when `LEGACY_HERMES_ROUTER_FALLBACK_ENABLED=false`

## Test Results

- **Python tests**: 112/112 passed
- **Action contract tests**: 6 new (email, schedule, work order dispatch + certification)
- **Idempotency tests**: Verified duplicate execution returns cached receipt
- **Failure injection**: Provider timeout, rejection, missing fields all return typed errors
