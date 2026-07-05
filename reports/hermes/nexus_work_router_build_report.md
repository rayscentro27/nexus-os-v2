# Hermes Work Router Build Report

**Generated:** 2026-07-05
**Status:** Routing Logic Defined — Live Integration Pending

---

## Intent Classification Patterns

| Pattern | Intent | Target Department |
|---------|--------|-------------------|
| `deploy *` / `ship *` / `release *` | deployment | deploy |
| `test *` / `run tests` / `spec *` | testing | testing |
| `lint *` / `format *` / `style *` | code_quality | code_quality |
| `migrate *` / `db *` / `schema *` | database | database |
| `scan *` / `security *` / `audit *` | security | security |
| `backup *` / `restore *` / `snapshot *` | database | database |
| `check *` / `health *` / `status *` | infrastructure | infrastructure |
| `notify *` / `alert *` / `email *` | communication | communication |
| `report *` / `analytics *` / `metrics *` | analytics | analytics |
| `sync *` / `import *` / `export *` | integration | integration |
| `cache *` / `invalidate *` / `clear *` | infrastructure | infrastructure |
| `webhook *` / `callback *` / `hook *` | integration | integration |
| `file *` / `upload *` / `download *` | storage | storage |
| `queue *` / `job *` / `task *` | infrastructure | infrastructure |
| `review *` / `approve *` / `gate *` | code_quality | code_quality |
| `fix *` / `patch *` / `hotfix *` | deploy | deploy |
| `monitor *` / `watch *` / `observe *` | monitoring | monitoring |
| `perf *` / `benchmark *` / `load *` | testing | testing |
| `rotate *` / `refresh *` / `renew *` | security | security |
| `drain *` / `flush *` / `clean *` | infrastructure | infrastructure |
| `process *` / `run *` / `execute *` | infrastructure | infrastructure |
| `ray *` / `decide *` / `approve *` | escalation | ray_review |
| `recovery *` / `resume *` / `retry *` | infrastructure | infrastructure |

## Routing Logic

```
1. Parse intent from user/system input
2. Match against classification patterns (regex)
3. If match → route to target department
4. If no match → escalate to ray_review for classification
5. Department receives work order
6. Department executes process
7. Process emits receipt
8. Receipt stored in Supabase
```

## Work Order Model

```typescript
interface WorkOrder {
  id: string;
  intent: string;
  department: string;
  status: 'pending' | 'queued' | 'in_progress' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  payload: Record<string, any>;
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  receipt_id?: string;
  error?: string;
}
```

## Department Mapping

| Department | Processes | Max Concurrent |
|------------|-----------|----------------|
| deploy | deploy_production, deploy_staging | 1 |
| testing | test_suite, performance_test | 3 |
| code_quality | code_review, lint_check | 2 |
| database | db_migration, db_backup | 1 |
| security | security_scan, credential_rotation | 2 |
| infrastructure | api_health_check, cache_invalidation, queue_drain, recovery_check | 5 |
| monitoring | log_analysis | 2 |
| communication | notification_dispatch | 3 |
| analytics | report_generation | 2 |
| integration | data_sync, webhook_delivery | 3 |
| storage | file_processing | 2 |
| ray_review | escalation routing | 10 |

## Next Actions

1. Create Supabase `work_orders` table
2. Implement intent classifier function
3. Wire router to Hermes queue
4. Add department load balancing
5. Implement dead letter queue for unroutable intents
6. Build routing dashboard in Command Center
