# Work Order Model

**Generated:** 2026-07-05

---

## Full Model Specification

### Supabase Table: `work_orders`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `uuid` | PK, default `gen_random_uuid()` | Unique identifier |
| `intent` | `text` | NOT NULL | Raw intent string |
| `department` | `text` | NOT NULL | Target department |
| `status` | `text` | NOT NULL, default 'pending' | Current status |
| `priority` | `text` | NOT NULL, default 'medium' | Priority level |
| `payload` | `jsonb` | default `'{}'` | Process input data |
| `created_by` | `text` | NOT NULL | Originator |
| `created_at` | `timestamptz` | default `now()` | Creation time |
| `started_at` | `timestamptz` | | Processing start |
| `completed_at` | `timestamptz` | | Processing end |
| `receipt_id` | `uuid` | FK → process_receipts.id | Linked receipt |
| `error` | `text` | | Error message if failed |
| `retry_count` | `integer` | default 0 | Retries attempted |
| `max_retries` | `integer` | default 3 | Retry limit |

### TypeScript Interface

```typescript
export type WorkOrderStatus = 'pending' | 'queued' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
export type WorkOrderPriority = 'low' | 'medium' | 'high' | 'critical';

export interface WorkOrder {
  id: string;
  intent: string;
  department: string;
  status: WorkOrderStatus;
  priority: WorkOrderPriority;
  payload: Record<string, unknown>;
  created_by: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  receipt_id?: string;
  error?: string;
  retry_count: number;
  max_retries: number;
}
```

### Status Flow

```
pending → queued → in_progress → completed
                                    ↓
                                  failed → (retry) → queued
                                    ↓
                                  cancelled (max retries exceeded)
```

### Examples

#### Deploy Request
```json
{
  "id": "wo-001",
  "intent": "deploy production v2.1.0",
  "department": "deploy",
  "status": "in_progress",
  "priority": "high",
  "payload": {
    "version": "2.1.0",
    "environment": "production",
    "rollback_enabled": true
  },
  "created_by": "hermes_router",
  "created_at": "2026-07-05T14:30:00Z",
  "started_at": "2026-07-05T14:30:05Z",
  "retry_count": 0,
  "max_retries": 0
}
```

#### Security Scan
```json
{
  "id": "wo-002",
  "intent": "security scan codebase",
  "department": "security",
  "status": "completed",
  "priority": "medium",
  "payload": {
    "scope": "full",
    "include_dependencies": true
  },
  "created_by": "scheduled_cron",
  "created_at": "2026-07-05T08:00:00Z",
  "started_at": "2026-07-05T08:00:02Z",
  "completed_at": "2026-07-05T08:02:15Z",
  "receipt_id": "receipt-abc-123",
  "retry_count": 0,
  "max_retries": 2
}
```

### Indexes

- `idx_work_order_status` on `status` (queue queries)
- `idx_work_order_dept` on `department, status` (department inbox)
- `idx_work_order_priority` on `priority, created_at` (priority ordering)
- `idx_work_order_created` on `created_at` (time-based queries)

### Row Level Security

- Service role: full access
- Authenticated: read on own created orders
- Department role: read/write on assigned department
- `ray` role: full access (override)
