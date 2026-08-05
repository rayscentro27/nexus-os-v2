# Hermes Runtime Path Inventory

## Execution Chain

```
Telegram update
  → process_telegram_updates()
    → process_command()
      → (A) Slash commands (18 handlers)
      → (B) try_hermes_platform() → LangGraph → capability helpers
      → (C) handle_nexus_pre_route() → tool_* functions → Supabase
      → (D) process_with_new_router() → draft engines → retrieval gate
      → (E) classify_message_intent() fallback
```

## Certified Paths (passing through dispatcher)

| Capability | Version | Handler | Source | Lifecycle |
|-----------|---------|---------|--------|-----------|
| get_client_count | v2 | hermes._get_client_count | Supabase client_profiles | certified_read |
| get_system_status | v1 | hermes._get_system_status | nexus_process_registry.json | certified_read |
| get_failure_report | v1 | hermes._get_failure_report | heartbeat_latest.json | certified_read |
| get_alpha_status | v1 | hermes._get_alpha_status | alpha_telegram_status.json | certified_read |
| client_acquisition_advisory | v1 | static response | internal | certified_read |
| create_opencode_prompt | v1 | hermes._create_opencode_prompt | internal context | certified_read |

## Quarantined Paths (blocked from production)

| Capability | Version | Reason | Lifecycle |
|-----------|---------|--------|-----------|
| send_email | v1 | Requires approval, handler not implemented | quarantined |
| schedule_report | v1 | Requires Temporal, not wired | quarantined |
| create_work_order | v1 | Requires approval flow | quarantined |

## Legacy Paths (not yet routed through dispatcher)

| Path | Data Source | Status |
|------|------------|--------|
| handle_nexus_pre_route tool_* functions | Supabase (6 tables) | migration candidate |
| process_with_new_router draft engines | External modules | migration candidate |
| hermes_direct_answer keyword branches | Multiple files | migration candidate |
| Slash command handlers (18) | Various JSON files | migration candidate |
| cmd_alpha_fallback | In-memory generation | deprecated |

## Data Sources

| Source | Type | Certified Path |
|--------|------|---------------|
| Supabase client_profiles | Table | get_client_count v2 |
| nexus_process_registry.json | Runtime file | get_system_status v1 |
| heartbeat_latest.json | Runtime file | get_failure_report v1 |
| alpha_telegram_status.json | Runtime file | get_alpha_status v1 |
| Supabase nexus_process_definitions | Table | legacy tool_get_process_status |
| Supabase nexus_process_runs | Table | legacy tool_get_failures |
| Supabase nexus_research_runs | Table | legacy tool_get_research_history |
| Supabase business_opportunities | Table | legacy tool_get_opportunities |
| oanda_practice_engine_status.json | Runtime file | legacy tool_get_trading_status |
| ray_review_queue_latest.json | Runtime file | legacy tool_get_pending_approvals |
