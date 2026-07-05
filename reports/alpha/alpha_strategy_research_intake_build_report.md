# Alpha Strategy Research Intake Build Report

**Generated:** 2026-07-05  
**Status:** Created  

## Decision Packet Model

See dedicated decision packet model report for full specification.

## Intake Types (13)

| # | Type | Description | Auto-Route |
|---|------|-------------|------------|
| 1 | Credit Analysis | Score factors, improvement path | Auto-score |
| 2 | Funding Match | Business profile → funding options | Auto-match |
| 3 | Grant Discovery | Location/industry → grant opportunities | Auto-match |
| 4 | Business Setup | Entity type, EIN, compliance | Checklist |
| 5 | Document Review | Uploaded doc validation | Ray Review |
| 6 | Application Prep | Funding app completion | Ray Review |
| 7 | Financial Analysis | Revenue, expenses, projections | Auto-score |
| 8 | Market Research | Industry, competition, positioning | Auto-score |
| 9 | Legal Review | Contracts, compliance, structure | Ray Review |
| 10 | Tax Strategy | Deductions, credits, planning | Auto-score |
| 11 | Insurance Review | Coverage, gaps, recommendations | Ray Review |
| 12 | Growth Planning | Scaling, hiring, expansion | Auto-score |
| 13 | Exit Strategy | Valuation, sale, transition | Ray Review |

## Scoring Engine

### Score Components

```typescript
interface IntakeScore {
  completeness: number;    // 0-100: How much data provided
  confidence: number;      // 0-100: How confident in analysis
  urgency: number;         // 0-100: Time sensitivity
  impact: number;          // 0-100: Potential business impact
  risk: number;            // 0-100: Risk level (lower = better)
}
```

### Scoring Formula

```
Total Score = (completeness × 0.25) + (confidence × 0.25) + 
              (urgency × 0.15) + (impact × 0.20) + ((100 - risk) × 0.15)
```

### Thresholds

| Score | Action | Priority |
|-------|--------|----------|
| 90-100 | Auto-approve | P4 |
| 70-89 | Fast-track review | P2 |
| 50-69 | Standard review | P3 |
| 30-49 | Enhanced review | P2 |
| 0-29 | Escalate to Ray | P1 |

## Route Trace

```
Intake Submitted
    ↓
Type Detection
    ↓
Auto-Route Decision
    ├─→ Auto-score path (types 1,2,3,6,8,10,12)
    │       ↓
    │   Score Calculation
    │       ↓
    │   Threshold Check
    │       ├─→ Auto-approve → Archive
    │       └─→ Needs review → Ray Review Queue
    │
    └─→ Manual review path (types 4,5,7,9,11,13)
            ↓
        Ray Review Queue
            ↓
        Review Assignment
            ↓
        Decision & Archive
```

## Archive vs Ray Review Routing

### Auto-Archive Criteria

- Score ≥ 90
- Complete data provided
- Low risk assessment
- Standard request type
- No flagged items

### Ray Review Required

- Score < 70
- Incomplete data
- High risk assessment
- Complex request type
- Flagged items present
- Client explicitly requests review

### Archive Structure

```typescript
interface IntakeArchive {
  id: string;
  type: IntakeType;
  client_id: string;
  score: IntakeScore;
  decision: 'approved' | 'rejected' | 'deferred';
  reviewer: 'auto' | 'ray';
  reviewed_at: string;
  notes: string;
  created_at: string;
}
```

## Next Actions

1. Build intake form components for all 13 types
2. Implement scoring engine
3. Create auto-route logic
4. Build Ray Review queue UI
5. Create archive system
6. Add audit trail logging
7. Test with sample data
8. Document intake type schemas
