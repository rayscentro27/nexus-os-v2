# Ray Review Item Model

**Generated:** 2026-07-05

---

## Full Model Specification

### Supabase Table: `ray_review_items`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `uuid` | PK, default `gen_random_uuid()` | Unique identifier |
| `type` | `text` | NOT NULL, CHECK IN ('decision','approval','escalation','audit') | Review type |
| `status` | `text` | NOT NULL, default 'pending' | Current status |
| `priority` | `text` | NOT NULL, default 'medium' | Priority level |
| `title` | `text` | NOT NULL | Short description |
| `description` | `text` | | Full context |
| `context` | `jsonb` | default `'{}'` | Arbitrary context payload |
| `requester` | `text` | NOT NULL | Who/what created this |
| `assigned_to` | `text` | default 'ray' | Assignee identifier |
| `created_at` | `timestamptz` | default `now()` | Creation time |
| `updated_at` | `timestamptz` | default `now()` | Last update time |
| `expires_at` | `timestamptz` | | Optional expiry |
| `decision` | `text` | | Approved/rejected value |
| `rationale` | `text` | | Why this decision |
| `process_receipt_id` | `uuid` | FK → process_receipts.id | Linked receipt |

### TypeScript Interface

```typescript
export type ReviewType = 'decision' | 'approval' | 'escalation' | 'audit';
export type ReviewStatus = 'pending' | 'awaiting_ray' | 'in_review' | 'approved' | 'rejected' | 'expired';
export type ReviewPriority = 'low' | 'medium' | 'high' | 'critical';

export interface RayReviewItem {
  id: string;
  type: ReviewType;
  status: ReviewStatus;
  priority: ReviewPriority;
  title: string;
  description: string;
  context: Record<string, unknown>;
  requester: string;
  assigned_to: string;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  decision?: string;
  rationale?: string;
  process_receipt_id?: string;
}
```

### Examples

#### Decision Request
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "decision",
  "status": "awaiting_ray",
  "priority": "high",
  "title": "Database migration strategy",
  "description": "Choose between zero-downtime migration and batch migration for user table refactor",
  "context": {
    "table": "users",
    "estimated_rows": 500000,
    "options": ["zero_downtime", "batch"]
  },
  "requester": "hermes:database_dept",
  "assigned_to": "ray",
  "created_at": "2026-07-05T10:00:00Z",
  "expires_at": "2026-07-06T10:00:00Z"
}
```

#### Approval Gate
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "type": "approval",
  "status": "awaiting_ray",
  "priority": "critical",
  "title": "Deploy v2.1.0 to production",
  "description": "All tests passing, security scan clean, ready for production deploy",
  "context": {
    "version": "2.1.0",
    "tests_passed": 142,
    "security_score": 98
  },
  "requester": "deploy_pipeline",
  "assigned_to": "ray",
  "created_at": "2026-07-05T12:00:00Z",
  "process_receipt_id": "abc-123-def"
}
```

### Indexes

- `idx_ray_review_status` on `status` (for queue queries)
- `idx_ray_review_priority` on `priority, created_at` (for prioritized display)
- `idx_ray_review_assigned` on `assigned_to, status` (for assignee queries)

### Row Level Security

- Service role: full access
- Authenticated: read-only on assigned items
- `ray` role: full read/write on awaiting items
