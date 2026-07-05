# Client Portal Guided Journey Audit

**Generated**: 2026-07-05

---

## Target Journey Assessment

### Step 1: Welcome / Onboarding
| Field | Status |
|-------|--------|
| Page/Component exists? | YES - `ClientPortalShell.jsx` |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | Name, email, phone |
| Supabase table needed | `client_profiles` |
| Local/report fallback possible | YES |
| Privacy risk | LOW |
| Client clarity | MEDIUM |
| Design quality | LOW (basic shell) |
| Prompt 2 build task | Build onboarding wizard with real form |

### Step 2: Credit Profile
| Field | Status |
|-------|--------|
| Page/Component exists? | YES - `/client/credit-repair` |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | Credit score, accounts, history |
| Supabase table needed | `credit_score_history` |
| Local/report fallback possible | YES |
| Privacy risk | HIGH (credit data) |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build credit profile view with real data |

### Step 3: Credit Utilization
| Field | Status |
|-------|--------|
| Page/Component exists? | YES - `/client/credit-profile-readiness` |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | Credit limits, balances, utilization |
| Supabase table needed | `credit_workflow_items` |
| Local/report fallback possible | YES |
| Privacy risk | HIGH |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build utilization calculator and recommendations |

### Step 4: Business Setup Profile
| Field | Status |
|-------|--------|
| Page/Component exists? | YES - `/client/business-profile-readiness` |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | See business_setup_profile_gap_map.md |
| Supabase table needed | `business_setup_items` |
| Local/report fallback possible | YES |
| Privacy risk | MEDIUM |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build business profile form |

### Step 5: Business Bankability
| Field | Status |
|-------|--------|
| Page/Component exists? | PARTIAL - via business-profile-readiness |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | Revenue, time in business, bank accounts |
| Supabase table needed | `funding_readiness_scores` |
| Local/report fallback possible | YES |
| Privacy risk | MEDIUM |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build bankability scorecard |

### Step 6: Funding Readiness
| Field | Status |
|-------|--------|
| Page/Component exists? | YES - `/client/funding-readiness` |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | Funding goal, documents, readiness score |
| Supabase table needed | `funding_readiness_scores` |
| Local/report fallback possible | YES |
| Privacy risk | MEDIUM |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build funding readiness dashboard |

### Step 7: Documents
| Field | Status |
|-------|--------|
| Page/Component exists? | YES - `/client/documents` |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | Document uploads, types, status |
| Supabase table needed | `client_documents` |
| Local/report fallback possible | YES |
| Privacy risk | HIGH (document storage) |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build document upload and management |

### Step 8: Recommendations
| Field | Status |
|-------|--------|
| Page/Component exists? | PARTIAL - via dashboard |
| Real data or placeholder? | PLACEHOLDER |
| Required fields | Recommendation items, priorities |
| Supabase table needed | `client_recommendations` |
| Local/report fallback possible | YES |
| Privacy risk | LOW |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build recommendations panel |

### Step 9: Resources / Optional Affiliate Links
| Field | Status |
|-------|--------|
| Page/Component exists? | PARTIAL - config exists |
| Real data or placeholder? | CONFIG ONLY |
| Required fields | Resource links, affiliate tracking |
| Supabase table needed | `partner_offers` |
| Local/report fallback possible | YES |
| Privacy risk | LOW |
| Client clarity | LOW |
| Design quality | LOW |
| Prompt 2 build task | Build resources page with affiliate links |

### Step 10: Request Review / Next Step
| Field | Status |
|-------|--------|
| Page/Component exists? | NO |
| Real data or placeholder? | N/A |
| Required fields | Review request, message |
| Supabase table needed | `task_requests` |
| Local/report fallback possible | NO |
| Privacy risk | LOW |
| Client clarity | N/A |
| Design quality | N/A |
| Prompt 2 build task | Build review request flow |

---

## Journey Completion Score

| Step | Exists | Real Data | Score |
|------|--------|-----------|-------|
| 1. Onboarding | ✓ | ✗ | 20 |
| 2. Credit Profile | ✓ | ✗ | 20 |
| 3. Credit Utilization | ✓ | ✗ | 20 |
| 4. Business Setup | ✓ | ✗ | 20 |
| 5. Business Bankability | Partial | ✗ | 15 |
| 6. Funding Readiness | ✓ | ✗ | 20 |
| 7. Documents | ✓ | ✗ | 20 |
| 8. Recommendations | Partial | ✗ | 15 |
| 9. Resources | Partial | Config | 25 |
| 10. Request Review | ✗ | N/A | 0 |
| **Average** | | | **17.5** |

---

## Key Finding

The client portal has **9 of 10 journey steps** with page/component existence, but **all show placeholder data**. Step 10 (Request Review) is completely missing. The journey structure is defined but not connected to real data or workflows.

---

## Recommendation for Prompt 2

1. Build onboarding wizard with real form fields
2. Connect credit profile to Supabase tables
3. Build credit utilization calculator
4. Build business profile form
5. Build funding readiness dashboard
6. Build document upload system
7. Build recommendations panel
8. Build resources/affiliate page
9. Build review request flow
10. Apply Got Funding design quality to all pages
