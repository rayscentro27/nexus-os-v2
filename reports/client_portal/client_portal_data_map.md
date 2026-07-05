# Client Portal Data Map

**Generated**: 2026-07-05

---

## Data Source Mapping

### Supabase Tables (from migrations)

| Table | Purpose | Used By | Status |
|-------|---------|---------|--------|
| `client_profiles` | Client identity & status | Onboarding, Dashboard | Schema exists |
| `client_tasks` | Client task list | Dashboard, Recommendations | Schema exists |
| `client_documents` | Document storage | Documents page | Schema exists |
| `readiness_scores` | Readiness assessment | Dashboard, Funding | Schema exists |
| `credit_score_history` | Credit score tracking | Credit Profile | Schema exists |
| `credit_workflow_items` | Credit workflow | Credit Utilization | Schema exists |
| `dispute_cases` | Dispute tracking | Credit Repair | Schema exists |
| `dispute_letter_drafts` | Letter drafts | Credit Repair | Schema exists |
| `business_setup_items` | Business profile | Business Setup | Schema exists |
| `business_profile_requirements` | Requirements | Business Setup | Schema exists |
| `funding_readiness_scores` | Funding readiness | Funding Readiness | Schema exists |
| `client_recommendations` | Recommendations | Recommendations | Schema exists |
| `partner_offers` | Affiliate offers | Resources | Schema exists |
| `client_workflow_stage_history` | Stage tracking | Journey progress | Schema exists |
| `client_mailings` | Mail tracking | Communications | Schema exists |
| `client_reminders` | Reminders | Dashboard | Schema exists |
| `task_requests` | Review requests | Request Review | Schema exists |
| `approval_cards` | Approval UI | Admin review | Schema exists |
| `admin_review_queue` | Admin queue | Admin review | Schema exists |
| `approved_client_guidance` | Guidance | Recommendations | Schema exists |
| `client_questions` | Q&A | Messages | Schema exists |
| `client_escalations` | Escalations | Messages | Schema exists |
| `proof_events` | Proof log | Audit trail | Schema exists |
| `tenant_memberships` | Multi-tenant | Auth | Schema exists |

---

## Frontend Data Flow

```
Client Portal Pages
  → ClientPortalShell.jsx (routing)
  → ClientPortalUI.jsx (main UI)
  → ClientPortalPages.jsx (page definitions)
  → [MOCK DATA] (src/data/clientPortalData.js)
  → [NOT CONNECTED TO SUPABASE]
```

---

## Current Mock Data Sources

| Page | Mock File | Real Source Needed |
|------|-----------|-------------------|
| Dashboard | `clientPortalData.js` | `client_profiles` + `client_tasks` + `readiness_scores` |
| Credit Repair | `creditFundingData.js` | `dispute_cases` + `dispute_letter_drafts` |
| Credit Profile | `creditFundingData.js` | `credit_score_history` |
| Business Profile | `clientPortalData.js` | `business_setup_items` |
| Business Opportunities | `businessOpportunitiesData.js` | `business_opportunities` |
| Funding Readiness | `creditFundingData.js` | `funding_readiness_scores` |
| Documents | `clientPortalData.js` | `client_documents` |
| Messages | `clientPortalData.js` | `client_questions` + `client_escalations` |
| Settings | `clientPortalData.js` | `client_profiles` |

---

## Recommendation for Prompt 2

1. Create `src/services/clientPortalDataLoader.ts`
2. Query Supabase tables using `supabaseClient`
3. Replace mock data in each page component
4. Add loading states and error handling
5. Add real-time updates for critical data
