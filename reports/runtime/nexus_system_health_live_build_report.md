# System Health Live Build Report

**Generated:** 2026-07-05
**Status:** Health Check Framework Defined — Live Wiring Pending

---

## 18 Health Checks Defined

### Infrastructure (6 checks)

| # | Check Name | Category | What It Validates |
|---|-----------|----------|-------------------|
| 1 | `supabase_connection` | Infrastructure | Database connection pool alive |
| 2 | `supabase_pool_usage` | Infrastructure | Connection pool utilization < 80% |
| 3 | `edge_function_latency` | Infrastructure | Edge function p95 < 500ms |
| 4 | `storage_availability` | Infrastructure | File storage bucket accessible |
| 5 | `auth_service` | Infrastructure | Auth service responding |
| 6 | `realtime_channel` | Infrastructure | WebSocket channel connected |

### Process Engine (5 checks)

| # | Check Name | Category | What It Validates |
|---|-----------|----------|-------------------|
| 7 | `process_queue_depth` | Process | Pending processes < 50 |
| 8 | `process_failure_rate` | Process | Failures last 5min < 5% |
| 9 | `receipt_integrity` | Process | Receipts match process registry |
| 10 | `process_timeout_rate` | Process | Timeouts last hour < 2% |
| 11 | `recovery_queue` | Process | Unrecovered interrupted processes = 0 |

### Hermes (4 checks)

| # | Check Name | Category | What It Validates |
|---|-----------|----------|-------------------|
| 12 | `hermes_queue_depth` | Hermes | Pending work orders < 100 |
| 13 | `hermes_routing_accuracy` | Hermes | Successful routings > 95% |
| 14 | `hermes_dept_load` | Hermes | No department overloaded > 2x avg |
| 15 | `hermes_dead_letters` | Hermes | Dead letter queue = 0 |

### Security (3 checks)

| # | Check Name | Category | What It Validates |
|---|-----------|----------|-------------------|
| 16 | `auth_failure_rate` | Security | Failed logins last 5min < 10 |
| 17 | `rate_limit_hits` | Security | Rate limit triggers < 50/min |
| 18 | `credential_rotation` | Security | API keys rotated within 90 days |

## Current Statuses

All checks return `mock` status until `systemHealthAdapter.ts` is wired to live data.

**Status values:** `pass` | `warn` | `fail` | `unknown` | `mock`

## Next Actions

1. Create Supabase tables for metrics collection
2. Wire `supabase_connection` check to actual pool stats
3. Wire `process_*` checks to process receipt aggregation
4. Wire `hermes_*` checks to work order stats
5. Add alert thresholds for warn/fail transitions
6. Build health score aggregation (weighted average)
7. Add historical trend storage for dashboards
