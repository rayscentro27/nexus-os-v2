# Recovery Receipt Model

**Generated:** 2026-07-05

---

## Full Model Specification

### Supabase Table: `recovery_receipts`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `uuid` | PK, default `gen_random_uuid()` | Unique identifier |
| `original_process_id` | `text` | NOT NULL | Interrupted process |
| `original_receipt_id` | `uuid` | FK → process_receipts.id | Failed receipt |
| `interrupted_at` | `timestamptz` | NOT NULL | Detection time |
| `recovered_at` | `timestamptz` | | Completion time |
| `recovery_type` | `text` | NOT NULL, CHECK IN ('auto','manual','forced') | Recovery method |
| `state_snapshot` | `jsonb` | default `'{}'` | Process state at interrupt |
| `next_best_tool` | `text` | NOT NULL | Recommended action |
| `recovery_actions` | `jsonb` | NOT NULL, default `'[]'` | Recovery steps |
| `status` | `text` | NOT NULL, default 'detected' | Current status |
| `error` | `text` | | Recovery failure reason |
| `created_at` | `timestamptz` | default `now()` | Record creation |

### TypeScript Interface

```typescript
export type RecoveryType = 'auto' | 'manual' | 'forced';
export type RecoveryStatus = 'detected' | 'recovering' | 'recovered' | 'failed';

export interface RecoveryAction {
  step: number;
  action: string;
  status: 'pending' | 'completed' | 'failed';
  timestamp?: string;
  error?: string;
}

export interface RecoveryReceipt {
  id: string;
  original_process_id: string;
  original_receipt_id: string;
  interrupted_at: string;
  recovered_at?: string;
  recovery_type: RecoveryType;
  state_snapshot: Record<string, unknown>;
  next_best_tool: string;
  recovery_actions: RecoveryAction[];
  status: RecoveryStatus;
  error?: string;
  created_at: string;
}
```

### Status Flow

```
detected → recovering → recovered
              ↓
            failed (max retries or manual abort)
```

### Examples

#### Auto Recovery
```json
{
  "id": "rec-001",
  "original_process_id": "deploy_production",
  "original_receipt_id": "rcpt-abc",
  "interrupted_at": "2026-07-05T15:00:00Z",
  "recovered_at": "2026-07-05T15:02:30Z",
  "recovery_type": "auto",
  "state_snapshot": {
    "step": "database_migration",
    "progress": 0.45,
    "last_log": "Altering users table..."
  },
  "next_best_tool": "rollback_deployment",
  "recovery_actions": [
    {"step": 1, "action": "snapshot_state", "status": "completed", "timestamp": "2026-07-05T15:00:01Z"},
    {"step": 2, "action": "rollback_migration", "status": "completed", "timestamp": "2026-07-05T15:01:30Z"},
    {"step": 3, "action": "verify_rollback", "status": "completed", "timestamp": "2026-07-05T15:02:30Z"}
  ],
  "status": "recovered",
  "created_at": "2026-07-05T15:00:00Z"
}
```

#### Manual Recovery
```json
{
  "id": "rec-002",
  "original_process_id": "data_sync",
  "original_receipt_id": "rcpt-def",
  "interrupted_at": "2026-07-05T12:00:00Z",
  "recovered_at": "2026-07-05T12:30:00Z",
  "recovery_type": "manual",
  "state_snapshot": {
    "sync_source": "external_api",
    "records_processed": 1500,
    "last_cursor": "eyJpZCI6MTUwMH0="
  },
  "next_best_tool": "cache_invalidation",
  "recovery_actions": [
    {"step": 1, "action": "ray_intervention", "status": "completed", "timestamp": "2026-07-05T12:05:00Z"},
    {"step": 2, "action": "resume_sync_from_cursor", "status": "completed", "timestamp": "2026-07-05T12:25:00Z"},
    {"step": 3, "action": "verify_data_integrity", "status": "completed", "timestamp": "2026-07-05T12:30:00Z"}
  ],
  "status": "recovered",
  "created_at": "2026-07-05T12:00:00Z"
}
```

### Indexes

- `idx_recovery_status` on `status` (active recovery queries)
- `idx_recovery_process` on `original_process_id` (process history)
- `idx_recovery_created` on `created_at` (time-based queries)

### Row Level Security

- Service role: full access
- `ray` role: full access (override)
- Authenticated: read-only on own process recoveries
- Department role: read on assigned department recoveries
