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

## Quarantined Capabilities

| Capability | Version | Semantic Def | Lifecycle | Owner | Handler | Source | Side Effect | Production |
|-----------|---------|-------------|-----------|-------|---------|--------|-------------|------------|
| send_email | v1 | (none) | quarantined | Ray | (not implemented) | resend_api | external | no |
| schedule_report | v1 | (none) | quarantined | Ray | (not implemented) | temporal_workflow | write | no |
| create_work_order | v1 | (none) | quarantined | Ray | (not implemented) | internal_registry | write | no |

## Certification Summary

- **Certified read**: 12 capabilities
- **Certified action**: 0 capabilities
- **Quarantined**: 3 capabilities
- **Draft**: 0 capabilities
- **Deprecated**: 0 capabilities
- **Disabled**: 0 capabilities

## Legacy Paths (Still Present, Not Certified)

These paths exist in the Telegram bridge but are NOT routed through the certified dispatcher:

1. `tool_get_process_status()` — Supabase query, no tenant filter, no auth
2. `tool_get_failures()` — Supabase query, no tenant filter, no auth
3. `tool_get_research_history()` — Supabase query, no tenant filter, no auth
4. `tool_get_opportunities()` — Supabase query, no tenant filter, no auth
5. `tool_get_alpha_status()` — JSON read, no auth
6. `tool_get_trading_status()` — JSON read, no auth
7. `tool_get_pending_approvals()` — JSON read, no auth
8. `tool_get_system_status()` — Aggregated from above
9. `tool_get_current_priorities()` — Aggregated
10. `hermes_direct_answer()` — Keyword branches
11. 18 slash command handlers

**Status**: Legacy fallback disabled (`LEGACY_HERMES_ROUTER_FALLBACK_ENABLED=false`). These paths are retained for backward compatibility but will not execute when the platform is enabled.

## Migration Status

### Completed
- Client count: Supabase-backed, tenant-filtered, certified
- Process status: Supabase-backed, certified
- Process failures: Supabase-backed, certified
- Research history: Supabase-backed, certified
- Opportunities: Supabase-backed, certified
- Alpha status: JSON-backed, certified
- Trading status: JSON-backed, certified
- Pending approvals: JSON-backed, certified
- System status: JSON-backed, certified
- Failure report: JSON-backed, certified
- Client acquisition advisory: Static, certified
- Create OpenCode prompt: Internal, certified

### Remaining
- Email action: Quarantined (requires Resend adapter)
- Scheduled report action: Quarantined (requires Temporal)
- Work order action: Quarantined (requires approval flow)
- Slash commands: 18 handlers, need migration to dispatcher
- Keyword direct answers: Need migration to certified capabilities
