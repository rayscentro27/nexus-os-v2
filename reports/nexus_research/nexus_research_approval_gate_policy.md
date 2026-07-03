# Nexus Research Approval Gate Policy

**Generated**: 2026-07-03  
**Purpose**: Define approval gates for all credit/funding research artifacts and outputs

---

## Approval Gate Levels

### Level 0: Auto-Approved (No Gate)
- Deterministic scorecard calculations
- Readiness tier assignments
- Internal status updates
- Demo/test data generation
- Build/test results

### Level 1: Admin Review
- Research artifact collection
- Evidence quality scoring
- Compliance flag identification
- Internal routing decisions
- Admin-only notes

### Level 2: Compliance Review
- Compliance flag resolution
- Policy guardrail updates
- FCRA/FDCPA compliance checks
- Disclosure requirement verification
- Legal disclaimer validation

### Level 3: Ray Review (Required for All Client-Facing)
- All client-facing content
- All credit/funding recommendations
- All dispute letter content
- All lender referrals
- All affiliate promotions
- All grant recommendations
- All education materials
- All funding approval gates

### Level 4: Operator Confirmation
- Payment collection
- Email/SMS sending
- External scheduling
- Production data mutation
- Live API connections

---

## Gate Application Rules

### Rule 1: Research Collection
```
Artifact collected → Evidence scored → Compliance flagged → Admin review → Stored
```
No external output at this stage.

### Rule 2: Research to Admin Notes
```
Artifact → Admin notes generated → Stored locally → No gate required
```
Admin notes are internal and do not require approval.

### Rule 3: Research to Client Education
```
Artifact → Education content drafted → Compliance reviewed → Ray Review → Approved → Client-facing
```
All client education requires full gate chain.

### Rule 4: Research to Recommendations
```
Artifact → Recommendation drafted → Compliance reviewed → Ray Review → Approved → Admin-only until Ray confirms
```
Recommendations are admin-only until Ray approves specific use.

### Rule 5: Research to Affiliate Promotion
```
Artifact → Affiliate offer evaluated → FTC disclosure added → Ray Review → Approved → Activation pending
```
All affiliate promotions require Ray approval and FTC compliance.

### Rule 6: Research to Dispute Content
```
Artifact → Dispute content drafted → FCRA compliance checked → Ray Review → Approved → Manual execution only
```
Dispute content is never automated. Always manual, always approved.

### Rule 7: Research to Funding Recommendation
```
Artifact → Funding recommendation drafted → Compliance checked → Ray Review → Approved → Admin-only
```
Funding recommendations are never guaranteed. Always advisory.

---

## Specific Gate Requirements

### Credit Repair Research
| Output | Gate Required |
|--------|---------------|
| Admin notes | Level 1 |
| Scorecard input | Level 0 |
| Client education | Level 3 |
| Dispute letter draft | Level 3 + FCRA |
| Credit improvement advice | Level 3 |

### Business Funding Research
| Output | Gate Required |
|--------|---------------|
| Admin notes | Level 1 |
| Checklist items | Level 0 |
| Client education | Level 3 |
| Funding recommendation | Level 3 |
| Lender referral | Level 3 |

### Grant Research
| Output | Gate Required |
|--------|---------------|
| Admin notes | Level 1 |
| Grant opportunity notes | Level 1 |
| Client education | Level 3 |
| Grant recommendation | Level 3 |

### Affiliate Research
| Output | Gate Required |
|--------|---------------|
| Admin notes | Level 1 |
| Affiliate evaluation | Level 1 |
| Client promotion | Level 3 + FTC |
| Link activation | Level 4 |

### Compliance Research
| Output | Gate Required |
|--------|---------------|
| Admin notes | Level 1 |
| Policy update | Level 2 + Ray Review |
| Guardrail change | Level 2 + Ray Review |
| Client-facing compliance note | Level 3 |

---

## Blocked Actions (No Gate — Always Blocked)

| Action | Reason |
|--------|--------|
| Automated dispute sending | Legal risk, no bureau connectors |
| Direct lender applications | Financial advice, no lender connectors |
| Funding approval guarantees | Compliance violation |
| Credit score guarantees | Compliance violation |
| Automated email/SMS | No Resend integration |
| Social publishing | No social connectors |
| Payment collection | No production Stripe |
| Live API connections | Blocked by design |
| Client data exposure | No secure workflow |
| Legal advice without license | Licensing violation |

---

## Gate Tracking

Every gate passage must be recorded:
- Who approved (ray, operator, system)
- When approved (ISO 8601 timestamp)
- What was approved (artifact_id, output_type)
- Gate level (0-4)
- Compliance notes (if any)
- Conditions (if any)

Gate records are stored locally and are not exposed to clients.

---

## Emergency Override

In case of urgent client need, Ray may:
1. Bypass normal gate chain
2. Document the override reason
3. Apply post-hoc compliance review
4. Record the override in gate tracking

Emergency overrides are limited to:
- Client education for active clients
- Time-sensitive grant deadlines
- Urgent funding deadline support

Emergency overrides do NOT apply to:
- Dispute sending
- Lender applications
- Payment collection
- External communications
