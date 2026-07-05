# Process Recovery Build Report

**Generated:** 2026-07-05
**Status:** Recovery Framework Defined — Implementation Pending

---

## Recovery Receipt Model

```typescript
interface RecoveryReceipt {
  id: string;
  original_process_id: string;
  original_receipt_id: string;
  interrupted_at: string;
  recovered_at: string;
  recovery_type: 'auto' | 'manual' | 'forced';
  state_snapshot: Record<string, any>;
  next_best_tool: string;
  recovery_actions: RecoveryAction[];
  status: 'detected' | 'recovering' | 'recovered' | 'failed';
}

interface RecoveryAction {
  step: number;
  action: string;
  status: 'pending' | 'completed' | 'failed';
  timestamp?: string;
  error?: string;
}
```

## Interrupted Work Detection

### Detection Mechanisms

| Method | Trigger | Check Interval |
|--------|---------|----------------|
| Receipt gap | Process started but no completion receipt | 60s |
| Timeout | Process exceeded max runtime | On timeout event |
| Error receipt | Process emitted failure receipt | Immediate |
| Health check | Process reported unhealthy | 30s |
| Manual flag | Ray flagged process for review | Immediate |

### Detection Flow

```
1. Monitor process receipts for gaps
2. If started_at exists but no completed_at after timeout → mark interrupted
3. Capture state snapshot at interruption point
4. Create recovery receipt with status 'detected'
5. Determine next-best-tool
6. Execute recovery actions
7. Mark as 'recovered' or 'failed'
```

## Next-Best-Tool Recommendation

| Failed Process | Next Best Tool | Reason |
|---------------|---------------|--------|
| deploy_production | rollback_deployment | Deployment failed, rollback safe |
| db_migration | db_backup_restore | Migration failed, restore from backup |
| security_scan | manual_audit | Automated scan failed, escalate |
| test_suite | lint_check | Tests failed, check basics first |
| data_sync | cache_invalidation | Sync failed, clear stale cache |
| webhook_delivery | queue_drain | Delivery failed, drain queue |
| credential_rotation | auth_service_check | Rotation failed, verify auth |
| cache_invalidation | storage_health_check | Invalidation failed, check storage |
| queue_drain | process_recovery | Drain failed, recover processes |
| file_processing | storage_availability | Processing failed, check storage |

## Recovery Receipt Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `uuid` | Unique recovery identifier |
| `original_process_id` | `string` | Process that was interrupted |
| `original_receipt_id` | `string` | Receipt that failed/timeout |
| `interrupted_at` | `string` | When interruption detected |
| `recovered_at` | `string` | When recovery completed |
| `recovery_type` | `enum` | How recovery was initiated |
| `state_snapshot` | `jsonb` | Process state at interruption |
| `next_best_tool` | `string` | Recommended recovery action |
| `recovery_actions` | `array` | Steps taken to recover |
| `status` | `enum` | Current recovery status |

## Next Actions

1. Create Supabase `recovery_receipts` table
2. Implement interrupt detection monitor
3. Build state snapshot capture
4. Implement next-best-tool lookup
5. Wire Recovery tab in Command Center
6. Add recovery notification to Ray Review
7. Test recovery flow with simulated failures
