# Hermes Capability Certification Matrix

| Capability | Version | Semantic Def | Lifecycle | Owner | Handler | Source | Tenant | Auth | Side Effect | Tests | Production |
|-----------|---------|-------------|-----------|-------|---------|--------|--------|------|-------------|-------|------------|
| get_client_count | v2 | production_client_summary@v1 | certified_read | Ray | hermes._get_client_count | Supabase client_profiles | goclear | admin | read | pass | yes |
| get_system_status | v1 | current_running_process_summary@v1 | certified_read | Ray | hermes._get_system_status | nexus_process_registry.json | global | admin | read | pass | yes |
| get_failure_report | v1 | current_failure_summary@v1 | certified_read | Ray | hermes._get_failure_report | heartbeat_latest.json | global | admin | read | pass | yes |
| get_alpha_status | v1 | current_alpha_status@v1 | certified_read | Ray | hermes._get_alpha_status | alpha_telegram_status.json | global | admin | read | pass | yes |
| client_acquisition_advisory | v1 | (none) | certified_read | Ray | static response | internal | global | admin | none | pass | yes |
| create_opencode_prompt | v1 | (none) | certified_read | Ray | hermes._create_opencode_prompt | internal context | global | admin | none | pass | yes |
| send_email | v1 | (none) | quarantined | Ray | (not implemented) | resend_api | - | - | external | - | no |
| schedule_report | v1 | (none) | quarantined | Ray | (not implemented) | temporal_workflow | - | - | write | - | no |
| create_work_order | v1 | (none) | quarantined | Ray | (not implemented) | internal_registry | - | - | write | - | no |

## Certification Summary

- **Certified read**: 6 capabilities
- **Certified action**: 0 capabilities
- **Quarantined**: 3 capabilities
- **Draft**: 0 capabilities
- **Deprecated**: 0 capabilities
- **Disabled**: 0 capabilities

## Uncertified Legacy Paths

These paths exist in the codebase but are NOT yet routed through the certified dispatcher:

1. `handle_nexus_pre_route()` → tool_get_process_status (Supabase)
2. `handle_nexus_pre_route()` → tool_get_failures (Supabase)
3. `handle_nexus_pre_route()` → tool_get_research_history (Supabase)
4. `handle_nexus_pre_route()` → tool_get_opportunities (Supabase)
5. `handle_nexus_pre_route()` → tool_get_alpha_status (JSON + launchctl)
6. `handle_nexus_pre_route()` → tool_get_trading_status (JSON + launchctl)
7. `handle_nexus_pre_route()` → tool_get_pending_approvals (JSON)
8. `handle_nexus_pre_route()` → tool_get_system_status (aggregated)
9. `process_with_new_router()` → draft engines
10. `hermes_direct_answer()` → keyword branches
11. 18 slash command handlers
