# Hermes Semantic Definitions

## Versioned Definitions

### production_client_summary@v1
- **Business meaning**: Count of production client profiles in GoClear tenant, excluding demo/cert/tester records
- **Included**: client_profiles WHERE tenant_id='goclear' AND source NOT IN ('tester_invitation', 'static_import', 'synthetic_certification')
- **Excluded**: tenant_demo_*, tenant-cert-*, tester_invitation, static_import, synthetic_certification
- **Tenant policy**: server_injected (goclear)
- **Status policy**: all statuses counted separately
- **Freshness**: real_time Supabase query
- **Zero valid**: yes
- **Certified**: 2026-08-05, live Ray test passed

### active_client_count@v1
- **Business meaning**: Count of production client profiles with status='active'
- **Derived from**: production_client_summary@v1 WHERE status='active'
- **Certified**: 2026-08-05

### onboarding_client_count@v1
- **Business meaning**: Count of production client profiles with status='onboarding'
- **Derived from**: production_client_summary@v1 WHERE status='onboarding'
- **Lifecycle**: draft

### current_running_process_summary@v1
- **Business meaning**: Count and list of currently running operational processes
- **Source**: nexus_process_registry.json WHERE status=running
- **Lifecycle**: draft

### current_failure_summary@v1
- **Business meaning**: Today's failures from heartbeat log
- **Source**: nexus_active_operator_heartbeat_latest.json
- **Lifecycle**: draft

### current_alpha_status@v1
- **Business meaning**: Current Alpha agent operational status
- **Source**: alpha_telegram_status.json
- **Lifecycle**: draft

### current_trading_status@v1
- **Business meaning**: Current Oanda practice trading engine status
- **Source**: oanda_practice_engine_status_latest.json
- **Lifecycle**: draft

### pending_approval_summary@v1
- **Business meaning**: Items awaiting Ray's approval
- **Source**: ray_review_queue_latest.json
- **Lifecycle**: draft
