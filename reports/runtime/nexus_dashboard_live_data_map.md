# Dashboard Live Data Map

**Generated:** 2026-07-05

---

## Tab → Data Source Mapping

| Tab | Data Source | Table/Module | Query |
|-----|------------|--------------|-------|
| Overview | Composite | `process_receipts` + `system_health_checks` | Aggregate scores |
| System Health | Adapter | `systemHealthAdapter.ts` | `getSystemHealthChecks()` |
| Process Monitor | Supabase | `process_receipts` | `select('*').order('created_at', {limit: 50})` |
| Hermes Queue | Supabase | `work_orders` | `select('*').eq('status', 'pending')` |
| Ray Review | Supabase | `ray_review_items` | `select('*').eq('status', 'awaiting_ray')` |
| Deployments | Supabase | `deployments` | `select('*').order('created_at', {limit: 20})` |
| Code Quality | Receipt | CI process receipts | `type = 'ci_pipeline'` |
| Security | Receipt | Security process receipts | `type = 'security_scan'` |
| Performance | Receipt | Telemetry receipts | `type = 'telemetry'` |
| Logs | Stream | Process stdout/stderr | `type = 'log_output'` |
| Database | Supabase | `information_schema` | Table row counts |
| APIs | Receipt | API gateway receipts | `type = 'api_request'` |
| Notifications | Derived | Health check failures | Filter `status = 'fail'` |
| Settings | Supabase | `app_config` | `select('*')` |
| Audit Trail | Receipt | All process receipts | `order('created_at', {limit: 100})` |
| Recovery | Receipt | Recovery receipts | `type = 'recovery'` |

## Data Refresh Strategy

- **Real-time:** System Health (3s poll), Process Monitor (5s poll)
- **Near real-time:** Hermes Queue, Ray Review (5s poll)
- **Periodic:** Overview, Code Quality, Security (30s poll)
- **On-demand:** Settings, Database, Logs (manual refresh)

## Missing Data Sources

- No `system_health_checks` table yet — computed from receipts
- No `deployments` table — needs creation
- No `app_config` table — needs creation
- Logs need streaming adapter (WebSocket or polling)
