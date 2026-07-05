# Business Setup Profile Gap Map

**Generated**: 2026-07-05

---

## Required Fields for Business Setup Profile

| Field | Category | Supabase Table | Status | Priority |
|-------|----------|---------------|--------|----------|
| Business Name | Identity | `business_setup_items` | Not built | HIGH |
| Entity Type | Identity | `business_setup_items` | Not built | HIGH |
| State | Identity | `business_setup_items` | Not built | HIGH |
| EIN Status | Compliance | `business_setup_items` | Not built | HIGH |
| Secretary of State Status | Compliance | `business_setup_items` | Not built | HIGH |
| NAICS/Business Category | Identity | `business_setup_items` | Not built | MEDIUM |
| Business Address | Contact | `business_setup_items` | Not built | MEDIUM |
| Business Phone | Contact | `business_setup_items` | Not built | MEDIUM |
| Business Email/Domain | Contact | `business_setup_items` | Not built | MEDIUM |
| Website | Contact | `business_setup_items` | Not built | LOW |
| DUNS Status | Compliance | `business_setup_items` | Not built | HIGH |
| Business Bank Account | Financial | `business_setup_items` | Not built | HIGH |
| Time in Business | Financial | `business_setup_items` | Not built | MEDIUM |
| Monthly Revenue Range | Financial | `business_setup_items` | Not built | MEDIUM |
| Documents Available | Documents | `client_documents` | Not built | MEDIUM |
| Funding Goal | Funding | `funding_readiness_scores` | Not built | HIGH |
| Bankability Gaps | Analysis | `funding_readiness_scores` | Not built | MEDIUM |
| Recommended Next Steps | Guidance | `client_recommendations` | Not built | MEDIUM |

---

## Gap Analysis

| Category | Fields | Built | Gap |
|----------|--------|-------|-----|
| Identity | 4 | 0 | 4 (100%) |
| Compliance | 3 | 0 | 3 (100%) |
| Contact | 4 | 0 | 4 (100%) |
| Financial | 3 | 0 | 3 (100%) |
| Documents | 1 | 0 | 1 (100%) |
| Funding | 1 | 0 | 1 (100%) |
| Analysis | 1 | 0 | 1 (100%) |
| Guidance | 1 | 0 | 1 (100%) |
| **Total** | **18** | **0** | **18 (100%)** |

---

## Database Schema (from migration 20260629090000)

```sql
CREATE TABLE business_setup_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  client_id TEXT NOT NULL,
  item_type TEXT NOT NULL,
  item_value JSONB,
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

**Note**: The table uses a flexible JSONB `item_value` field rather than dedicated columns. This means the schema supports all fields but the application layer needs to define the field structure.

---

## Recommendation for Prompt 2

1. Define field structure in application layer (not just JSONB)
2. Build business profile form with all 18 fields
3. Add validation for required fields (Identity, Compliance, Financial)
4. Add progress indicator (% complete)
5. Connect to funding readiness scoring
6. Apply Got Funding design quality
