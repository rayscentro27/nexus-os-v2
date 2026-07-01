# Reports Center Activation Latest

**Generated:** 2026-07-01T19:45:00Z
**Data Sources:** reports/ directory listing

---

## Summary

| Metric | Value |
|--------|-------|
| Total Reports | 62 |
| Categories | 10 |
| Runtime Files | 576 |

---

## Categories

### 1. Operations Status
System operations and process status reports.
- nexus_operations_status_latest.json
- nexus_process_inventory_latest.json
- nexus_scheduler_inventory_latest.json
- hermes_operations_status_latest.json
- full_nexus_reality_audit_latest.json

### 2. Hermes AI
Hermes AI agent configuration and status reports.
- hermes_chat_live_model_smoke_latest.json
- hermes_chat_live_model_trace.json
- hermes_durable_memory_plan.json
- hermes_live_model_activation_plan.json
- hermes_live_model_browser_verification_latest.json
- hermes_live_send_path_trace.json
- hermes_model_cost_policy.json
- hermes_model_infrastructure_inventory_latest.json
- hermes_response_trace.json
- hermes_restriction_audit.json
- hermes_second_brain_index_latest.json
- hermes_web_search_status_latest.json

### 3. Supabase Data
Supabase database status and seed reports.
- supabase_truth_audit.json
- static_to_supabase_seed_dry_run_latest.json
- static_to_supabase_seed_plan.json
- research_live_row_shape_audit.json

### 4. Trading
Trading engine and strategy reports.
- trading_lab_proof_latest.json
- trading/imports/

### 5. YouTube Research
YouTube research engine status reports.
- nexus_youtube_research_status_latest.json
- youtube_research_live_proof_latest.json

### 6. Live Connection
Live data connection implementation and proof reports.
- live_connection_implementation_plan.json
- live_seed_execution_latest.json
- manual_live_connection_verification.md
- nexus_live_connection_proof.json

### 7. Activation Baselines
Phase 2 activation baseline and process activity reports.
- nexus_phase2_activation_baseline.json
- nexus_process_activity_latest.json
- automation_scheduler_proof_latest.json
- credit_funding_activation_latest.json
- system_health_activation_latest.json
- reports_center_activation_latest.json
- settings_config_status_latest.json
- cli_tool_registry_latest.json
- marketing_drafts_activation_latest.json

### 8. Content
Content and marketing related reports.
- content/

### 9. SEO
SEO optimization reports.
- seo/

### 10. Runtime
Runtime operations and automation reports.
- runtime/ (576 files)

---

## Latest Reports by Timestamp

| Report | Timestamp |
|--------|-----------|
| hermes_operations_status_latest.json | 2026-07-01T14:10:00Z |
| nexus_operations_status_latest.json | 2026-07-01T19:39:27Z |
| nexus_process_inventory_latest.json | 2026-07-01T19:39:27Z |
| nexus_scheduler_inventory_latest.json | 2026-07-01T19:39:27Z |
| hermes_model_infrastructure_inventory_latest.json | 2026-07-01T19:39:28Z |

---

## Directory Structure

```
reports/
├── content/
├── manual_publish/
├── research/
├── runtime/          (576 files)
├── seo/
├── trading/
└── [root reports]
```

---

## Blockers

1. Reports center reads local files only
2. No Supabase table for report registry
3. Uses reportRegistryData.js for UI

## Next Safe Action

Seed report registry to Supabase; wire UI to live reads; keep local files as backup.
