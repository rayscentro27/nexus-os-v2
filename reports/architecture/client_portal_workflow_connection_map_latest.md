# Client Portal Workflow Connection Map

## Legend
- **Status**: LIVE | PARTIAL | FALLBACK | BROKEN | UNKNOWN
- **Data Source**: Live Supabase | Static `clientPortalData.js` | Hybrid
- **Write**: Indicates if workflow writes to Supabase

---

## 1. Login
- **Client route**: `/client/login`
- **UI component**: `ClientLoginPage`
- **Data source**: Supabase Auth (`supabase.auth.signInWithPassword`)
- **Read helper**: `useSession()` from `src/components/auth.tsx`
- **Write helper**: None (auth only)
- **Admin visibility**: None
- **Hermes guidance**: None
- **Verification SQL**: N/A
- **Current status**: LIVE
- **Blocker**: None
- **Exact patch needed**: None

## 2. Dashboard Readiness
- **Client route**: `/client/dashboard`
- **UI component**: `ClientDashboard` (in `ClientPortalPages.jsx`)
- **Data source**: Hybrid — `clientPortalData.js` fallback + `loadClientDashboardLiveData()` when `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`
- **Read helper**: `loadClientDashboardLiveData()` → queries `client_profiles`, `client_tasks`, `readiness_scores`, `client_documents`
- **Write helper**: None
- **Admin visibility**: None (client-only)
- **Hermes guidance**: `HermesGuidancePanel` + `ClientGuidePanel` with `what_do_i_do_next`, `documents_needed`, `can_i_apply_for_funding_now`
- **Verification SQL**:
  ```sql
  SELECT * FROM client_profiles WHERE client_id = '<resolved_client_id>';
  SELECT * FROM readiness_scores WHERE client_id = '<resolved_client_id>';
  ```
- **Current status**: PARTIAL
- **Blocker**: Fallback data hides live rows when `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=false`
- **Exact patch needed**: Ensure `loadClientDashboardLiveData()` resolves signed-in client context (fixed in R2); remaining pages still use static data

## 3. Credit Profile
- **Client route**: `/client/credit-profile`
- **UI component**: `CreditProfilePage`
- **Data source**: Static `clientPortalData.creditProfileReadiness`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: `ClientGuidePanel` with `how_to_improve_credit`, `what_do_i_do_next`, `what_goclear_is_reviewing`
- **Verification SQL**: N/A (no live query)
- **Current status**: FALLBACK
- **Blocker**: Page does not call `loadClientDashboardLiveData()` or `clientPortalDataAdapter.loadReadinessScores()`
- **Exact patch needed**: Wire `CreditProfilePage` to live data via adapter or live data loader

## 4. Credit Utilization
- **Client route**: `/client/credit-utilization`
- **UI component**: `CreditUtilizationPage`
- **Data source**: Static `clientPortalData.creditProfileReadiness`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: `ClientGuidePanel` with `how_to_improve_credit`, `what_do_i_do_next`, `can_i_apply_for_funding_now`
- **Verification SQL**: N/A
- **Current status**: FALLBACK
- **Blocker**: No live data connection
- **Exact patch needed**: Wire to live readiness scores or credit_workflow_items

## 5. Document Requirements
- **Client route**: `/client/documents`
- **UI component**: `ClientDocumentsPage`
- **Data source**: Hybrid — `clientPortalData.documents` fallback + live `client_documents` via `loadClientDashboardLiveData()`
- **Read helper**: `loadClientDashboardLiveData()` → `client_documents`
- **Write helper**: None (read-only tracking)
- **Admin visibility**: Admin drawer in `ClientsPanel.jsx` shows live `client_documents` rows
- **Hermes guidance**: `ClientGuidePanel` with `documents_needed`, `what_goclear_is_reviewing`, `what_do_i_do_next`
- **Verification SQL**:
  ```sql
  SELECT * FROM client_documents WHERE client_id = '<resolved_client_id>' AND client_visible = true;
  ```
- **Current status**: PARTIAL
- **Blocker**: R2 fixed hardcoded client_id; R1 fixed RLS insert; display now works for signed-in client
- **Exact patch needed**: None (complete for live mode)

## 6. Document Upload
- **Client route**: `/client/documents`
- **UI component**: `DocumentUploadZone`
- **Data source**: Supabase Storage + `client_documents` metadata insert
- **Read helper**: `resolveClientContextForCurrentUser()` from `src/lib/clientAuthContext.ts`
- **Write helper**: `writeDocumentMetadata()` → `supabase.storage.from('client-documents').upload()` + `supabase.from('client_documents').insert()`
- **Admin visibility**: Admin drawer shows uploaded files; `goclear_review_status = pending_review` flags for review
- **Hermes guidance**: None
- **Verification SQL**:
  ```sql
  SELECT * FROM client_documents WHERE source = 'client_portal_upload' ORDER BY created_at DESC LIMIT 5;
  SELECT * FROM storage.objects WHERE bucket_id = 'client-documents' AND name LIKE '<resolved_client_id>%';
  ```
- **Current status**: PARTIAL
- **Blocker**: RLS policy `client_documents_client_insert_own` required and added in R1; identity mapping fixed in R1
- **Exact patch needed**: None (complete for live mode)

## 7. GoClear Review Status
- **Client route**: `/client/request-review` + `/client/documents`
- **UI component**: `RequestReviewPage`, `ClientDocumentsPage`
- **Data source**: Hybrid — `clientPortalData` fallback + live `client_tasks` (`goclear_review_status`)
- **Read helper**: `loadClientDashboardLiveData()` → `client_tasks`
- **Write helper**: `handleSubmitReview()` → `client_tasks.insert()` with `category = 'review_request'`
- **Admin visibility**: `ClientsPanel.jsx` shows `review_request` tasks
- **Hermes guidance**: `ClientGuidePanel` with `what_goclear_is_reviewing`, `what_do_i_do_next`
- **Verification SQL**:
  ```sql
  SELECT * FROM client_tasks WHERE client_id = '<resolved_client_id>' AND category = 'review_request';
  ```
- **Current status**: PARTIAL
- **Blocker**: None for basic flow; dedup works client-side
- **Exact patch needed**: None (complete for live mode)

## 8. Business Setup Checklist
- **Client route**: `/client/business-setup`
- **UI component**: `BusinessSetupPage`
- **Data source**: Static `clientPortalData.businessProfileReadiness`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: `ClientGuidePanel` with `business_profile_next_step`, `documents_needed`, `what_do_i_do_next`
- **Verification SQL**: N/A
- **Current status**: FALLBACK
- **Blocker**: No live data connection
- **Exact patch needed**: Wire to `business_profile_requirements` table via adapter

## 9. Business Bankability
- **Client route**: `/client/business-bankability`
- **UI component**: `BusinessBankabilityPage`
- **Data source**: Static `clientPortalData.businessProfileReadiness`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: `ClientGuidePanel` with `business_profile_next_step`, `documents_needed`, `what_do_i_do_next`
- **Verification SQL**: N/A
- **Current status**: FALLBACK
- **Blocker**: No live data connection
- **Exact patch needed**: Wire to live business profile data

## 10. Funding Readiness
- **Client route**: `/client/funding-readiness`
- **UI component**: `FundingReadinessPage`
- **Data source**: Static `clientPortalData.fundingReadiness`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: `ClientGuidePanel` with `can_i_apply_for_funding_now`, `why_not_funding_ready`, `documents_needed`
- **Verification SQL**: N/A
- **Current status**: FALLBACK
- **Blocker**: No live data connection
- **Exact patch needed**: Wire to `funding_readiness_scores` and `readiness_scores`

## 11. Recommendations/Tools
- **Client route**: `/client/recommendations`, `/client/resources`
- **UI component**: `RecommendationsPage`, `ResourcesPage`
- **Data source**: Static `clientPortalData.businessOpportunities`, `partner_offers`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: `ClientGuidePanel` with `what_opportunity_should_i_focus_on`, `can_i_apply_for_funding_now`, `what_do_i_do_next`
- **Verification SQL**: N/A
- **Current status**: FALLBACK
- **Blocker**: No live data connection
- **Exact patch needed**: Wire to `business_opportunities` and `partner_offers` tables

## 12. Request Review
- **Client route**: `/client/request-review`
- **UI component**: `RequestReviewPage`
- **Data source**: Hybrid — `clientPortalData` fallback + live `client_tasks` via `loadClientDashboardLiveData()`
- **Read helper**: `loadClientDashboardLiveData()` → `client_tasks`
- **Write helper**: `handleSubmitReview()` → `client_tasks.insert()` with `category = 'review_request'`
- **Admin visibility**: Admin drawer in `ClientsPanel.jsx` shows review requests
- **Hermes guidance**: `ClientGuidePanel` with `what_goclear_is_reviewing`, `what_do_i_do_next`, `can_i_apply_for_funding_now`
- **Verification SQL**:
  ```sql
  SELECT * FROM client_tasks WHERE client_id = '<resolved_client_id>' AND category = 'review_request' AND status = 'pending_admin_review';
  ```
- **Current status**: PARTIAL
- **Blocker**: None for basic flow
- **Exact patch needed**: None (complete for live mode)

## 13. Messages/Support
- **Client route**: `/client/messages`
- **UI component**: `ClientMessagesPage`
- **Data source**: Static `clientPortalData.messages`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: None
- **Verification SQL**: N/A
- **Current status**: FALLBACK (read-only preview)
- **Blocker**: No live messaging backend
- **Exact patch needed**: None (out of scope for current patch)

## 14. Hermes Guidance
- **Client route**: All client pages (sidebar panel)
- **UI component**: `HermesGuidancePanel`, `ClientGuidePanel`
- **Data source**: Static `generateClientGuidance()` + `getGuidanceForStep()` fallback
- **Read helper**: `generateClientGuidance(statuses)` from `src/clientPortal/clientGuidance.ts`
- **Write helper**: None
- **Admin visibility**: Separate admin Hermes panel in `NexusAdminUI.jsx`
- **Hermes guidance**: Core integration
- **Verification SQL**: N/A
- **Current status**: PARTIAL
- **Blocker**: Guidance uses demo `statuses` from `clientPortalData.js`; live status propagation incomplete
- **Exact patch needed**: Propagate live statuses from `useClientPortalData` through `ClientPortalShell` to `HermesGuidancePanel`

## 15. Admin Client Review
- **Client route**: N/A (admin-only)
- **UI component**: `ClientsPanel.jsx` (in `NexusAdminUI.jsx`)
- **Data source**: Static `clientsData.js` + live `client_documents`/`client_tasks` via Supabase
- **Read helper**: `loadSection('clients', clientsList)` from `src/lib/liveDataLoader`
- **Write helper**: None (UI-only; Approve/Hold set local receipt state)
- **Admin visibility**: Admin-only
- **Hermes guidance**: `onAskHermes` callback
- **Verification SQL**:
  ```sql
  SELECT * FROM client_documents WHERE client_id = '<any>';
  SELECT * FROM client_tasks WHERE category = 'review_request';
  ```
- **Current status**: PARTIAL
- **Blocker**: Admin guard now in place (R4); data fetching partial
- **Exact patch needed**: Wire full client list to live `client_profiles`/`tenant_memberships`

## 16. Admin Document Review
- **Client route**: N/A (admin-only)
- **UI component**: `ClientsPanel.jsx` → `ClientDetailDrawer`
- **Data source**: Live `client_documents` rows + Storage file listing
- **Read helper**: Direct Supabase queries in drawer `useEffect`
- **Write helper**: None
- **Admin visibility**: Admin-only
- **Hermes guidance**: None
- **Verification SQL**:
  ```sql
  SELECT * FROM client_documents WHERE client_id = '<target_client_id>';
  ```
- **Current status**: PARTIAL
- **Blocker**: None
- **Exact patch needed**: None

## 17. Admin Route Security
- **Client route**: `/admin`, `/admin/*`
- **UI component**: `AdminGuard` → `AuthGate` → `NexusAdminUI`
- **Data source**: N/A (guard only)
- **Read helper**: `checkAdminAccess()` from `src/lib/adminAccess.ts`
- **Write helper**: None
- **Admin visibility**: N/A
- **Hermes guidance**: None
- **Verification SQL**:
  ```sql
  SELECT role FROM tenant_memberships WHERE user_id = '<auth_user_id>';
  SELECT active FROM admin_users WHERE id = '<auth_user_id>';
  ```
- **Current status**: LIVE (R4 fix)
- **Blocker**: None
- **Exact patch needed**: None

## 18. Email/Resend Templates
- **Client route**: N/A
- **UI component**: Not identified in audited files
- **Data source**: N/A
- **Read helper**: N/A
- **Write helper**: N/A
- **Admin visibility**: N/A
- **Hermes guidance**: N/A
- **Verification SQL**: N/A
- **Current status**: UNKNOWN
- **Blocker**: Not found in current codebase
- **Exact patch needed**: N/A

## 19. Stripe/Subscription Readiness
- **Client route**: `/client/settings`
- **UI component**: `ClientSettingsPage`
- **Data source**: Static `clientPortalData.clientProfile.subscriptionStatus`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None
- **Hermes guidance**: None
- **Verification SQL**: N/A
- **Current status**: FALLBACK
- **Blocker**: No live subscription connection
- **Exact patch needed**: Wire to `subscription_memberships` and `payments_status` tables

## 20. Affiliate/Recommended Tools
- **Client route**: `/client/recommendations`, `/client/resources`
- **UI component**: `RecommendationsPage`, `ResourcesPage`
- **Data source**: Static `clientPortalData.businessOpportunities.partnerOffers`
- **Read helper**: None (static)
- **Write helper**: None
- **Admin visibility**: None (admin sees same data via `NexusAdminUI.jsx` → `GoClearWorkspace`)
- **Hermes guidance**: `ClientGuidePanel` with `what_opportunity_should_i_focus_on`
- **Verification SQL**: N/A
- **Current status**: FALLBACK
- **Blocker**: No live data connection
- **Exact patch needed**: Wire to `partner_offers` and `business_opportunities` tables
