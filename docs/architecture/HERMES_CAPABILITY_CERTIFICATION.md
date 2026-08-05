# Hermes Capability Certification Matrix

## Certified Read Capabilities

| Capability | Version | Semantic Def | Lifecycle | Owner | Handler | Source | Tenant | Auth | Tests | Production |
|-----------|---------|-------------|-----------|-------|---------|--------|--------|------|-------|------------|
| get_client_count | v2 | production_client_summary@v1 | certified_read | Ray | hermes._get_client_count | Supabase client_profiles | goclear | admin | pass | yes |
| get_system_status | v1 | current_running_process_summary@v1 | certified_read | Ray | hermes._get_system_status | nexus_process_registry.json | global | admin | pass | yes |
| get_failure_report | v1 | current_failure_summary@v1 | certified_read | Ray | hermes._get_failure_report | heartbeat_latest.json | global | admin | pass | yes |
| get_alpha_status | v1 | current_alpha_status@v1 | certified_read | Ray | hermes._get_alpha_status | alpha_telegram_status.json | global | admin | pass | yes |
| client_acquisition_advisory | v1 | (none) | certified_read | Ray | static response | internal | global | admin | pass | yes |
| create_opencode_prompt | v1 | (none) | certified_read | Ray | hermes._create_opencode_prompt | internal context | global | admin | pass | yes |
| process_status | v1 | process_definition_summary@v1 | certified_read | Ray | hermes._get_process_status | Supabase nexus_process_definitions,nexus_process_runs | server_injected | admin | pass | yes |
| process_failures | v1 | process_failure_summary@v1 | certified_read | Ray | hermes._get_process_failures | Supabase nexus_process_runs | server_injected | admin | pass | yes |
| research_history | v1 | research_run_summary@v1 | certified_read | Ray | hermes._get_research_history | Supabase nexus_research_runs,nexus_research_results | server_injected | admin | pass | yes |
| opportunities | v1 | business_opportunity_summary@v1 | certified_read | Ray | hermes._get_opportunities | Supabase business_opportunities | server_injected | admin | pass | yes |
| trading_status | v1 | current_trading_status@v1 | certified_read | Ray | hermes._get_trading_status | oanda_practice_engine_status_latest.json | global | admin | pass | yes |
| pending_approvals | v1 | pending_approval_summary@v1 | certified_read | Ray | hermes._get_pending_approvals | ray_review_queue_latest.json | global | admin | pass | yes |

## Certified Action Capabilities

| Capability | Version | Lifecycle | Owner | Handler | Source | Durability | Confirmation | Idempotency | Tests | Production |
|-----------|---------|-----------|-------|---------|--------|------------|--------------|-------------|-------|------------|
| send_approved_email | v1 | certified_action | Ray | actions.send_approved_email | resend_api | immediate | required | mission_id_based | pass | yes |
| schedule_report | v1 | certified_action_local_file | Ray | actions.schedule_report | local_file_scheduler | local_file_durable | required | mission_id_based | pass | yes |
| create_work_order | v1 | certified_action | Ray | actions.create_work_order | supabase_table:task_requests | database_durable | required | mission_id_based | pass | yes |

## Certification Summary

- **Certified read**: 12 capabilities
- **Certified action**: 3 capabilities (1 immediate, 1 local-file-durable, 1 database-durable)
- **Quarantined**: 0 capabilities
- **Draft**: 0 capabilities
- **Deprecated**: 0 capabilities
- **Disabled**: 0 capabilities

## Temporal Truth Audit

### Current State

| Component | Status |
|-----------|--------|
| Temporal server | Running (dev mode, port 7233) |
| Temporal CLI | Available at /usr/local/bin/bin/temporal |
| TEMPORAL_WORKFLOWS_ENABLED | **false** |
| Temporal adapter mode | Direct invocation (no server) |
| schedule_report implementation | **LOCAL_FILE_DURABLE** |

### Explanation

The Temporal server is running in development mode, but the `TEMPORAL_WORKFLOWS_ENABLED` flag is set to `false`. This means:

1. The Temporal adapter falls back to direct function invocation
2. Schedule definitions are stored as JSON files in `data/runtime/scheduled_reports/`
3. There is NO durable Temporal workflow execution
4. Timer persistence depends on file system durability

### Classification

**`LOCAL_FILE_DURABLE`** — Schedule definitions persist to disk. Execution depends on a worker process polling the scheduled_reports directory. Worker restart requires the schedule files to remain intact.

### Upgrade Path

To achieve `TEMPORAL_DURABLE`:
1. Set `TEMPORAL_WORKFLOWS_ENABLED=true` in runtime.env
2. Register activities with the Temporal adapter
3. Start the Temporal worker process
4. Migrate existing schedule files to Temporal workflows

## Action Capability Details

### send_approved_email_v1

**Required fields**: recipient, subject, body
**Optional fields**: reply_to, template_id, related_mission
**Flow**: TaskSpec → dispatcher → validate fields → idempotency check → Resend Edge Function → receipt → trace
**Idempotency**: mission_id based, stored in action_receipts/
**Provider**: Resend via Supabase Edge Function
**Durability**: Immediate execution (no scheduling)

### schedule_report_v1

**Required fields**: report_definition, execution_time
**Optional fields**: timezone (default America/Phoenix), recurrence, delivery_channel, report_format
**Flow**: TaskSpec → dispatcher → validate fields → idempotency check → store schedule JSON → worker picks up → execute read capability → format → Telegram delivery
**Idempotency**: mission_id based, stored in action_receipts/
**Durability**: LOCAL_FILE_DURABLE (JSON files in data/runtime/scheduled_reports/)
**Receipt**: schedule_id, execution_time, report_definition

### create_work_order_v1

**Required fields**: title, description, source_context
**Optional fields**: owner, priority, due_date, linked_opportunity, linked_research, assigned_agent
**Flow**: TaskSpec → dispatcher → validate fields → idempotency check → Supabase insert → receipt → trace
**Idempotency**: mission_id based, stored in action_receipts/
**Storage**: Supabase task_requests table
**Durability**: DATABASE_DURABLE

## Live Certification Status

| Capability | Unit Tests | Integration Tests | Live Ray Test | Final Status |
|-----------|------------|-------------------|---------------|--------------|
| send_approved_email | Pass | Ready | Pending | certified_action |
| schedule_report | Pass | Ready | Pending | certified_action_local_file |
| create_work_order | Pass | Ready | Pending | certified_action |

**Note**: Live Ray certification requires actual Telegram-originated messages. Unit tests verify the contract and handler logic but do not prove end-to-end delivery.

## Test Results

- **Python tests**: 112/112 passed
- **Action contract tests**: 6 (email, schedule, work order dispatch + certification)
- **Idempotency tests**: Verified duplicate execution returns cached receipt
- **Failure injection**: Provider timeout, rejection, missing fields all return typed errors
