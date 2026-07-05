# Alpha Decision Packet Model

**Generated:** 2026-07-05  
**Status:** Specification  

## Full Model Specification

```typescript
interface AlphaDecisionPacket {
  id: string;
  type: IntakeType;
  client_id: string;
  org_id: string;
  
  // Core data
  data: Record<string, any>;  // Type-specific payload
  metadata: PacketMetadata;
  
  // Scoring
  score: IntakeScore;
  
  // Routing
  route: 'auto_archive' | 'ray_review' | 'escalated';
  priority: 'P1' | 'P2' | 'P3' | 'P4';
  
  // Decision
  decision: Decision | null;
  
  // Audit
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
  archived_at: string | null;
}
```

## Fields

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `type` | IntakeType | One of 13 intake types |
| `client_id` | UUID | Client reference |
| `org_id` | UUID | Organization reference |
| `data` | JSONB | Type-specific data payload |
| `metadata` | JSONB | Submission metadata |

### Metadata

```typescript
interface PacketMetadata {
  source: 'portal' | 'api' | 'import' | 'manual';
  submission_id: string;
  ip_address: string | null;
  user_agent: string | null;
  files_attached: string[];
  referenced_packets: string[];
}
```

## Scoring Factors

### Completeness (0-100)

| Factor | Weight | Description |
|--------|--------|-------------|
| Required fields | 40% | All required fields present |
| Optional fields | 20% | Bonus for extra data |
| File attachments | 20% | Supporting documents |
| History context | 20% | Previous packet references |

### Confidence (0-100)

| Factor | Weight | Description |
|--------|--------|-------------|
| Data quality | 30% | Clean, validated data |
| Source reliability | 25% | Trusted submission source |
| Consistency | 25% | Matches known patterns |
| Verification | 20% | Cross-referenced data |

### Urgency (0-100)

| Factor | Weight | Description |
|--------|--------|-------------|
| Deadline proximity | 40% | How soon is the deadline |
| Client tier | 25% | Higher tier = higher urgency |
| Opportunity window | 25% | Time-sensitive opportunity |
| Dependencies | 10% | Blocks other processes |

### Impact (0-100)

| Factor | Weight | Description |
|--------|--------|-------------|
| Funding amount | 35% | Size of potential funding |
| Business growth | 30% | Growth potential unlocked |
| Risk mitigation | 20% | Risks addressed |
| Strategic value | 15% | Long-term benefits |

### Risk (0-100)

| Factor | Weight | Description |
|--------|--------|-------------|
| Data gaps | 30% | Missing critical information |
| Red flags | 25% | Potential issues identified |
| Complexity | 25% | Multi-factor decision |
| Precedent | 20% | Similar past outcomes |

## Thresholds

```typescript
interface ScoringThresholds {
  auto_approve: { min: 90; max: 100 };
  fast_track: { min: 70; max: 89 };
  standard: { min: 50; max: 69 };
  enhanced: { min: 30; max: 49 };
  escalate: { min: 0; max: 29 };
}
```

## Decision Model

```typescript
interface Decision {
  outcome: 'approved' | 'rejected' | 'deferred' | 'escalated';
  reviewer: 'auto' | 'ray' | 'system';
  reason: string;
  conditions: string[];
  next_steps: string[];
  decided_at: string;
}
```

## Next Actions

1. Create database migration for `decision_packets` table
2. Implement scoring engine functions
3. Build route decision logic
4. Create decision recording system
5. Add audit trail triggers
6. Build query/reporting views
