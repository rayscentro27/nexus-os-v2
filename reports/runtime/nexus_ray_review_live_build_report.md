# Ray Review Live Build Foundation

**Generated:** 2026-07-05
**Status:** Model Defined — UI Integration Pending

---

## RayReviewItem Model Defined

```typescript
interface RayReviewItem {
  id: string;
  type: 'decision' | 'approval' | 'escalation' | 'audit';
  status: 'pending' | 'awaiting_ray' | 'in_review' | 'approved' | 'rejected' | 'expired';
  priority: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  context: Record<string, any>;
  requester: string;
  assigned_to: 'ray' | string;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  decision?: string;
  rationale?: string;
}
```

## Status Flow

```
pending → awaiting_ray → in_review → approved | rejected
                                        ↓
                                    expired (if past expires_at)
```

## Review Types

| Type | Trigger | Auto-Approve | SLA |
|------|---------|-------------|-----|
| `decision` | Architecture choice needed | No | 24h |
| `approval` | Deploy/security gate | No | 4h |
| `escalation` | Process failure exceeds threshold | No | 1h |
| `audit` | Post-execution review | Yes (if pass) | 7d |

## Approval Flow

1. Process or Hermes generates review request
2. Item created in `ray_review_items` with status `pending`
3. Router assigns to `ray` → status becomes `awaiting_ray`
4. Ray opens item → status becomes `in_review`
5. Ray approves/rejects → status becomes `approved`/`rejected`
6. Downstream process resumes or halts

## UI Integration Plan

- **Ray Review tab** in Command Center shows queue of `awaiting_ray` items
- Detail modal shows context, requester, and decision buttons
- Approved items trigger callback to originating process
- Rejected items halt originating process with rationale
- Real-time updates via Supabase subscription on `ray_review_items`

## Next Actions

1. Create Supabase `ray_review_items` table
2. Wire Ray Review tab to real query
3. Add real-time subscription for live updates
4. Build approve/reject action buttons
5. Add notification when new item appears
6. Implement expiry cleanup job
