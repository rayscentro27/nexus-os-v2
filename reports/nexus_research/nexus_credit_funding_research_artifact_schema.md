# Nexus Credit & Funding Research Artifact Schema

**Generated**: 2026-07-03  
**Purpose**: Standardize how credit/funding research artifacts are collected, classified, and routed

---

## Schema Definition

Every research artifact must include:

```json
{
  "artifact_id": "string — unique identifier (nexus-res-YYYY-NNN)",
  "source_path": "string — local file path or reference",
  "category": "enum — one of the defined categories",
  "title": "string — human-readable title",
  "source_type": "enum — research_type",
  "date_collected": "string — ISO 8601 date",
  "summary": "string — 1-3 sentence summary",
  "evidence_quality": "enum — evidence_quality_tier",
  "compliance_flags": "array — compliance considerations",
  "client_safe": "boolean — safe for client-facing use",
  "admin_only": "boolean — restricted to admin/Ray Review",
  "funding_stage": "enum — funding_readiness_stage",
  "credit_stage": "enum — credit_readiness_stage",
  "recommended_workflow": "string — which workflow this supports",
  "ray_review_required": "boolean — requires Ray Review before use",
  "allowed_output_type": "array — what outputs this can generate",
  "blocked_output_type": "array — what outputs this cannot generate",
  "provenance": "object — {hash, verified, verified_by, verified_at}",
  "tags": "array — freeform tags for search"
}
```

---

## Enums

### Categories
| Category | Description |
|----------|-------------|
| `credit_repair` | Credit report analysis, dispute strategies, score improvement |
| `credit_utilization` | Utilization scoring, reduction strategies, optimization |
| `business_setup` | LLC, EIN, DUNS, NAICS, business entity formation |
| `fundability` | Fundability scoring, improvement strategies, bankability |
| `business_funding` | Business credit, loans, SBA, credit lines, financing |
| `grants` | Grant databases, programs, application requirements |
| `lender_program` | Lender criteria, underwriting, documentation requirements |
| `affiliate_offer` | Affiliate programs, referral opportunities, partner offers |
| `client_education` | Educational content for clients, general knowledge |
| `compliance` | FCRA, FDCPA, licensing, disclosure requirements |
| `manual_note` | Operator-created notes, observations, evaluations |

### Source Types
| Source Type | Description |
|-------------|-------------|
| `web_research` | Information gathered from web sources |
| `government_source` | Official government databases or publications |
| `industry_report` | Industry analysis or market research |
| `partner_submission` | Information from affiliate partners |
| `operator_note` | Manually created by Ray or operator |
| `client_contribution` | Provided by client through approved workflow |
| `public_database` | Publicly available database or directory |
| `academic_source` | Academic or research institution source |

### Evidence Quality Tiers
| Tier | Description |
|------|-------------|
| `verified` | Confirmed from multiple reliable sources |
| `credible` | From a single reliable source |
| `unverified` | Not yet confirmed |
| `demo` | Synthetic/example data for testing |
| `opinion` | Subjective assessment, not factual |

### Funding Stages
| Stage | Description |
|-------|-------------|
| `pre_setup` | Before business entity exists |
| `entity_formed` | LLC/Corp formed, no EIN |
| `ein_obtained` | EIN registered, no DUNS |
| `duns_registered` | DUNS active, no bank account |
| `bank_account_open` | Business bank account active |
| `credit_building` | Building business credit |
| `funding_ready` | Ready for funding applications |
| `funded` | Has received funding |

### Credit Stages
| Stage | Description |
|-------|-------------|
| `unknown` | Credit status not yet assessed |
| `assessed` | Credit reviewed, no action taken |
| `disputes_pending` | Disputes filed, awaiting results |
| `improving` | Active credit improvement in progress |
| `optimized` | Credit at target levels |
| `needs_review` | Credit needs re-assessment |

---

## Categories in Detail

### credit_repair
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, compliance notes, client education (approved) |
| Blocked outputs | Direct dispute letters, bureau contact, guaranteed removals |
| Compliance flags | FCRA, dispute accuracy, client disclosure |
| Ray Review required | Yes, for all client-facing |

### credit_utilization
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, scorecard recommendations, client education (approved) |
| Blocked outputs | Guaranteed score increases, specific payoff advice |
| Compliance flags | General education only, not financial advice |
| Ray Review required | Yes, for client-facing |

### business_setup
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, checklist items, client education (approved) |
| Blocked outputs | Legal advice, tax advice, guaranteed outcomes |
| Compliance flags | Legal/tax disclaimers required |
| Ray Review required | Yes, for recommendations |

### business_funding
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, funding path research, client education (approved) |
| Blocked outputs | Guaranteed approvals, direct lender applications |
| Compliance flags | No funding guarantees, lending disclaimers |
| Ray Review required | Yes, for all recommendations |

### grants
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, grant opportunity research, client education (approved) |
| Blocked outputs | Guaranteed grant approval, application submission |
| Compliance flags | Must verify grant legitimacy |
| Ray Review required | Yes, for recommendations |

### lender_program
| Field | Value |
|-------|-------|
| Allowed outputs | Admin-only matching notes |
| Blocked outputs | Client-facing lender recommendations, direct applications |
| Compliance flags | No funding guarantees |
| Ray Review required | Yes, for all use |

### affiliate_offer
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, Ray Review proposals |
| Blocked outputs | Client-facing promotions, activated links |
| Compliance flags | FTC disclosure required |
| Ray Review required | Yes, for all promotions |

### client_education
| Field | Value |
|-------|-------|
| Allowed outputs | Client-facing content (after approval) |
| Blocked outputs | Specific financial advice, guaranteed outcomes |
| Compliance flags | Educational framing required |
| Ray Review required | Yes, before client-facing |

### compliance
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, policy updates, guardrail changes |
| Blocked outputs | Legal advice, compliance guarantees |
| Compliance flags | Legal review required |
| Ray Review required | Yes, for policy changes |

### manual_note
| Field | Value |
|-------|-------|
| Allowed outputs | Admin notes, research inputs |
| Blocked outputs | Client-facing without review |
| Compliance flags | Depends on content |
| Ray Review required | Depends on content |

---

## Provenance Schema

```json
{
  "hash": "string — SHA-256 of source file (optional, for integrity)",
  "verified": "boolean — has this been verified by operator",
  "verified_by": "string — who verified (ray, operator, system)",
  "verified_at": "string — ISO 8601 timestamp",
  "source_url": "string — original source URL if web-based",
  "access_date": "string — when source was accessed"
}
```

---

## Validation Rules

1. `artifact_id` must be unique
2. `category` must be one of the defined enums
3. `evidence_quality` cannot be `verified` unless `provenance.verified` is true
4. `client_safe` must be false if `compliance_flags` is non-empty
5. `ray_review_required` must be true if `client_safe` is true
6. `blocked_output_type` must not overlap with `allowed_output_type`
7. `source_path` must reference an existing file or be a valid reference
