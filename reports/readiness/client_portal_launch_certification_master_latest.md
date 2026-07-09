# Client Portal Launch Certification Master — Nexus OS v2

## Legend
- **UI loads**: Page renders without console errors
- **Correct live data shows**: Live Supabase data appears when env flag is set
- **Fallback does not override live data**: Demo data does not replace live rows
- **Button works**: Click handlers execute correctly
- **Supabase read works**: Live queries return data
- **Supabase write works**: Live inserts/updates succeed (if applicable)
- **Admin can see it**: Admin route shows the data/panel
- **Hermes guidance matches**: Guidance reflects current page data
- **Mobile usable**: Responsive layout works
- **Security safe**: No data leaks, proper auth guards

---

## Workflow Certification Matrix

| # | Workflow | UI Loads | Live Data | Fallback Safe | Button Works | Supabase Read | Supabase Write | Admin Visible | Hermes Sync | Mobile | Security | Status |
|---|----------|----------|-----------|---------------|--------------|---------------|----------------|---------------|-------------|--------|----------|--------|
| 1 | Login | YES | N/A | N/A | YES | N/A | N/A | N/A | N/A | YES | YES | GREEN |
| 2 | Dashboard | YES | PARTIAL | YES | YES | PARTIAL | NO | NO | PARTIAL | YES | YES | YELLOW |
| 3 | Credit Profile | YES | NO | YES | YES | NO | NO | NO | PARTIAL | YES | YES | YELLOW |
| 4 | Credit Utilization | YES | NO | YES | YES | NO | NO | NO | PARTIAL | YES | YES | YELLOW |
| 5 | Document Requirements | YES | YES | YES | YES | YES | NO | PARTIAL | YES | YES | YES | GREEN |
| 6 | Document Upload | YES | YES | YES | YES | YES | YES | YES | YES | N/A | YES | GREEN |
| 7 | GoClear Review Status | YES | PARTIAL | YES | YES | PARTIAL | YES | PARTIAL | YES | PARTIAL | YES | GREEN |
| 8 | Business Setup | YES | NO | YES | YES | NO | NO | NO | PARTIAL | YES | YES | YELLOW |
| 9 | Business Bankability | YES | NO | YES | YES | NO | NO | NO | PARTIAL | YES | YES | YELLOW |
| 10 | Funding Readiness | YES | NO | YES | YES | NO | NO | NO | PARTIAL | YES | YES | YELLOW |
| 11 | Recommendations | YES | NO | YES | YES | NO | NO | NO | PARTIAL | YES | YES | YELLOW |
| 12 | Request Review | YES | PARTIAL | YES | GATED | PARTIAL | YES | PARTIAL | YES | PARTIAL | YES | GREEN |
| 13 | Messages | YES | NO | YES | NO | NO | NO | NO | N/A | YES | YES | YELLOW |
| 14 | Hermes Guidance | YES | PARTIAL | YES | YES | PARTIAL | NO | PARTIAL | YES | YES | YES | YELLOW |
| 15 | Admin Client Review | YES | PARTIAL | YES | YES | PARTIAL | NO | YES | N/A | YES | YES | GREEN |
| 16 | Admin Document Review | YES | YES | YES | YES | YES | NO | YES | N/A | YES | YES | GREEN |
| 17 | Admin Route Security | YES | N/A | N/A | YES | N/A | N/A | N/A | N/A | YES | YES | GREEN |
| 18 | Email/Resend | UNKNOWN | NO | N/A | UNKNOWN | NO | NO | NO | N/A | UNKNOWN | UNKNOWN | RED |
| 19 | Stripe/Subscriptions | YES | NO | YES | NO | NO | NO | NO | PARTIAL | YES | YES | YELLOW |
| 20 | Affiliate/Tools | YES | NO | YES | YES | NO | NO | NO | PARTIAL | YES | YES | YELLOW |

---

## Readiness by User Tier

### Ray Solo Testing
- **Can test now**: YES
- **Prerequisites**: Set `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`, apply RLS migration `20260707140000`
- **Green workflows**: Login, Dashboard (partial), Documents (live upload), Request Review, Admin routes (guarded)
- **Yellow workflows**: Credit, Utilization, Business, Funding, Recommendations, Hermes, Messages
- **Blockers**: None for basic testing

### 1 Outside Tester
- **Can invite**: CONDITIONAL
- **Prerequisites**:
  1. Apply RLS migration to live Supabase
  2. Create tester auth account in Supabase Auth
  3. Create `tenant_memberships` row with `role = 'client'`
  4. Create `client_profiles` row linked to membership
  5. Set `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`
- **Green workflows**: Login, Documents (upload), Request Review
- **Yellow workflows**: Dashboard (partial), Credit, Utilization, Business, Funding
- **Blockers**: Yellow workflows show demo data instead of live

### 3 Outside Testers
- **Can invite**: CONDITIONAL
- **Prerequisites**: Same as 1 tester, plus 2 more accounts
- **Green workflows**: Same as 1 tester
- **Yellow workflows**: Same as 1 tester
- **Blockers**: None beyond 1-tester blockers

### 10 Outside Testers
- **Can invite**: NOT YET
- **Prerequisites**: Same as above, plus load testing
- **Blockers**: Yellow workflows need live data connections; no bulk provisioning automation

### Paid Clients
- **Can onboard**: NOT YET
- **Prerequisites**:
  1. All yellow workflows connected to live data
  2. Stripe/subscription integration
  3. Email/notification system
  4. Production env with `VITE_ENABLE_LIVE_SUPABASE_TEST_CLIENT=true`
  5. Admin review workflow fully automated
- **Blockers**: 8 of 20 workflows are still fallback-only

### Real Sensitive Data
- **Safe**: NO
- **Prerequisites**:
  1. All RLS policies verified
  2. Admin guard tested with real admin accounts
  3. No service-role keys in frontend
  4. No sensitive data in demo/fallback mode
  5. Production audit of all write paths
- **Blockers**: Admin guard is new; real-data testing incomplete

---

## Top Connection Gaps

1. **Dashboard/credit/business/funding pages** still use static `clientPortalData.js` instead of live tables
2. **Hermes guidance** uses demo `statuses` from `clientPortalData.js`; live status propagation incomplete
3. **Stripe/subscription** not connected to `subscription_memberships` or `payments_status`
4. **Email/resend** templates not implemented
5. **Mobile menu toggle** is hidden (`display: none`)
6. **Header icon buttons** misrouted to `/client/resources`
7. **`/client/preview`** references missing `ClientPreviewPage`
8. **`clientPortalDataAdapter.ts`** uses hardcoded `client_test_julius_erving` instead of resolved context
