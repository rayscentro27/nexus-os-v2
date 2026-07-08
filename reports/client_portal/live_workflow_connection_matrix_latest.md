# Workflow Connection Matrix — Client Portal

**Date:** 2026-07-08
**Starting Commit:** 71b9dd4

---

| Workflow | Client UI | Supabase Table/Storage | Admin Review | Hermes Guidance | Status |
|---|---|---|---|---|---|
| Login | ClientLoginPage (email/password) | auth.users (Supabase Auth) | N/A | N/A | LIVE |
| Dashboard data | ClientDashboard (static + live option) | client_profiles, readiness_scores, client_tasks | ClientsPanel (static) | HermesGuidancePanel (dynamic) | PARTIAL |
| Upload credit report | DocumentUploadZone | client-documents (storage) | ClientsPanel (storage list) | generateClientGuidance (status flag) | PARTIAL |
| Upload proof of address | DocumentUploadZone | client-documents (storage) | ClientsPanel (storage list) | generateClientGuidance (status flag) | PARTIAL |
| Credit utilization action | CreditUtilizationPage | credit_workflow_items (seed only) | Not visible | Static guidance | PLACEHOLDER |
| Business setup checklist | BusinessSetupPage | business_profile_requirements (seed only) | Not visible | Static guidance | PLACEHOLDER |
| Business bankability checklist | BusinessBankabilityPage | business_profile_requirements (seed only) | Not visible | Static guidance | PLACEHOLDER |
| Funding readiness review | FundingReadinessPage | readiness_scores (read) | Not visible | Static guidance | PARTIAL |
| Recommendations/tools | RecommendationsPage | Static demo data | Not visible | Static guidance | PLACEHOLDER |
| Request review | RequestReviewPage (disabled button) | Not wired | Not implemented | Static guidance | PLACEHOLDER |
| Messages/support | ClientMessagesPage (static demo) | Not wired | Not visible | N/A | PLACEHOLDER |
| Sign out | ClientSidebar → supabase.auth.signOut() | auth.users (session clear) | N/A | N/A | LIVE |

---

## Status Definitions

- **LIVE:** Fully connected end-to-end, real data flows
- **PARTIAL:** UI exists, some data connection, incomplete workflow
- **PLACEHOLDER:** UI exists, demo/static data only, no real backend
- **BROKEN:** Non-functional or errors
- **NOT REQUIRED FOR TESTERS:** Out of scope for tester phase

---

## Key Gaps

1. **Dashboard data:** Live data path exists but requires env flag; admin sees static data
2. **Document upload:** Storage works, metadata table not written to
3. **Credit/Business workflows:** Tables exist, seeded by script, frontend uses static data
4. **Request review:** Button disabled, no submission mechanism
5. **Messages:** Static demo data only, no real messaging
