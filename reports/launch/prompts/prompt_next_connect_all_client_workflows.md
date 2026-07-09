# Next Implementation Prompt — Connect All Client Workflows

## Context
This prompt is generated from the Nexus OS v2 client portal connection map audit (all `reports/architecture/*_latest.md` files). Do not redesign. Do not change RLS. Do not break existing live/fallback behavior.

## Priority 1: Admin Access Security
**Status**: LIVE (R4 fix complete)
**Action**: Verify guard in production. Run `python3 scripts/checks/check_admin_route_guard.py`. Confirm `theworldzmine@gmail.com` cannot access `/admin`. Confirm Ray/admin can.

## Priority 2: Live/Fallback Mode Correctness
**Status**: PARTIAL
**Blocker**: Multiple pages still use static `clientPortalData.js` even when `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`
**Exact patch**:
1. In `src/services/clientDashboardLiveData.ts`, remove hardcoded `TEST_CLIENT_ID` as primary; make resolved context the only path for live mode.
2. In `src/lib/clientPortalDataAdapter.ts`, add `loadBusinessProfileRequirements()`, `loadApprovedClientGuidance()`, `loadFundingReadinessScores()` functions if not present.
3. In `src/pages/client/ClientPortalPages.jsx`, wire `CreditProfilePage`, `CreditUtilizationPage`, `BusinessSetupPage`, `BusinessBankabilityPage`, `FundingReadinessPage`, `RecommendationsPage`, `ResourcesPage` to live data via adapter or live data loader.
4. Ensure each page shows live data banner when `displayDocs`/`liveData` is present, fallback otherwise.

## Priority 3: Dashboard + Documents + Request Review
**Status**: PARTIAL → GREEN
**Blocker**: Dashboard, Documents, and Request Review partially live. Missing: live credit scores, live business profile, live funding readiness.
**Exact patch**:
1. `ClientDashboard` — wire `readinessScores` and `tasks` to live data from `loadClientDashboardLiveData()`
2. `CreditProfilePage` — wire to `readiness_scores` for credit profile readiness
3. `CreditUtilizationPage` — wire to `credit_workflow_items` for utilization data
4. `RequestReviewPage` — wire `fundingReadiness` to live data; verify dedup against live `client_tasks`

## Priority 4: Admin Review Visibility
**Status**: PARTIAL
**Blocker**: Admin drawer in `ClientsPanel.jsx` shows live `client_documents` and `review_request` tasks, but full client list is still static.
**Exact patch**:
1. Wire client list in `ClientsPanel.jsx` to live `client_profiles` / `tenant_memberships`
2. Add filter/search for admin to find clients
3. Show live document count and pending review count per client in list view

## Priority 5: Hermes Guidance Sync
**Status**: PARTIAL
**Blocker**: `HermesGuidancePanel` uses demo `statuses` from `clientPortalData.js`; live status propagation incomplete
**Exact patch**:
1. In `ClientPortalShell.jsx`, propagate live `statuses` from `useClientPortalData` through `PortalLiveStatusContext`
2. In `HermesGuidancePanel`, consume live `statuses` instead of static demo values
3. In `ClientGuidePanel`, ensure `responseFor()` regex matches reflect current page context

## Priority 6: Business Setup / Funding Readiness
**Status**: FALLBACK
**Blocker**: No live data connection to `business_profile_requirements`, `funding_readiness_scores`
**Exact patch**:
1. Add `loadBusinessProfileRequirements()` to `clientPortalDataAdapter.ts`
2. Wire `BusinessSetupPage` and `BusinessBankabilityPage` to live data
3. Wire `FundingReadinessPage` to `funding_readiness_scores` and `readiness_scores`

## Priority 7: Fixed UI Zip Import
**Status**: Deferred per mission rules
**Action**: Do not run fixed UI zip import unless explicitly authorized by Ray.

## Priority 8: Stripe/Subscriptions
**Status**: FALLBACK
**Blocker**: No connection to `subscription_memberships` or `payments_status`
**Exact patch**:
1. Add `loadSubscriptionMemberships()` and `loadPaymentsStatus()` to `clientPortalDataAdapter.ts`
2. Wire `ClientSettingsPage` to live subscription data
3. Add subscription status badge to `ClientPortalShell.jsx` header

## Priority 9: Affiliate Tools
**Status**: FALLBACK
**Blocker**: No live connection to `partner_offers` and `business_opportunities`
**Exact patch**:
1. Add `loadPartnerOffers()` and `loadBusinessOpportunities()` to `clientPortalDataAdapter.ts`
2. Wire `RecommendationsPage` and `ResourcesPage` to live partner/business data
3. Add opportunity filtering based on client readiness scores

## Non-Gobers (Do Not Patch)
- Email/Resend templates — not implemented, out of scope
- `/client/preview` — missing file, out of scope unless Ray requests
- Header icon misrouting — UX issue, not a data connection blocker
- Mobile menu toggle hidden — UX issue, not a data connection blocker
