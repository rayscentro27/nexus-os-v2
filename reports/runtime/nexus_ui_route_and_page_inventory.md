# Nexus UI Route and Page Inventory

**Generated**: 2026-07-05

---

## Top-Level Routes

| Route | Component | Purpose | Data Source | Status |
|-------|-----------|---------|-------------|--------|
| `/` (default) | `AuthGate > NexusAdminUI` | Admin dashboard | Auth required | Live |
| `/update-password` | `UpdatePasswordPage` | Password reset | Supabase Auth | Live |
| `/client/*` | `ClientPortalRoot` | Client portal | Mixed | Partial |
| `?ui-smoke=1` | `NexusAdminUI` (no auth) | Dev smoke test | None | Dev only |

---

## Client Portal Sub-Routes

| Route | Label | Component | Data Source | Status |
|-------|-------|-----------|-------------|--------|
| `/client/dashboard` | Dashboard | ClientPortalShell | Mock | Placeholder |
| `/client/credit-repair` | Credit Repair | ClientPortalShell | Mock | Placeholder |
| `/client/credit-profile-readiness` | Credit Profile Readiness | ClientPortalShell | Mock | Placeholder |
| `/client/business-profile-readiness` | Business Profile Readiness | ClientPortalShell | Mock | Placeholder |
| `/client/business-opportunities` | Business Opportunities | ClientPortalShell | Mock | Placeholder |
| `/client/funding-readiness` | Funding Readiness | ClientPortalShell | Mock | Placeholder |
| `/client/documents` | Documents | ClientPortalShell | Mock | Placeholder |
| `/client/messages` | Messages | ClientPortalShell | Mock | Placeholder |
| `/client/settings` | Settings | ClientPortalShell | Mock | Placeholder |

---

## Admin Shell Tabs (16)

| Tab | Key | Label | Component | Data Source | Mock Risk |
|-----|-----|-------|-----------|-------------|-----------|
| 1 | `command` | Command Center | MissionControl.tsx | Local data | HIGH |
| 2 | `health` | System Health | SystemHealthPanel.jsx | Local data | HIGH |
| 3 | `jobs` | Agent Jobs | NexusOperationsPanel.jsx | Local data | HIGH |
| 4 | `approvals` | Approvals | (via RayReview) | Local data | HIGH |
| 5 | `review` | Ray Review Queue | RayReviewQueueView.tsx | Local data | HIGH |
| 6 | `goclear` | GoClear / Apex | CreditFundingPanel.jsx | Local data | MEDIUM |
| 7 | `opportunities` | Opportunity Lab | BusinessOpportunitiesPanel.jsx | Local data | MEDIUM |
| 8 | `intake` | Source Intake & Review | SourceIntakeReviewPage.tsx | Local data | MEDIUM |
| 9 | `creative` | Creative Studio | MarketingDraftCenter.jsx | Local data | MEDIUM |
| 10 | `design` | Design Library | (via Creative Studio) | Local data | MEDIUM |
| 11 | `trading` | Trading Lab | (via Research Engine) | Local data | MEDIUM |
| 12 | `seo` | SEO / Marketing | MarketingDraftsPanel.jsx | Local data | MEDIUM |
| 13 | `models` | Model Router | (via Hermes) | Local data | MEDIUM |
| 14 | `integrations` | Integrations | (via Connector Registry) | Local data | MEDIUM |
| 15 | `ops` | Ops & Improvements | NexusOperationsPanel.jsx | Local data | MEDIUM |
| 16 | `events` | Events Feed | (via System Health) | Local data | MEDIUM |

---

## Netlify Function Routes

| Route | Function | Purpose | Status |
|-------|----------|---------|--------|
| `/api/alpha/search` | `alpha-search.mjs` | Web search via SearXNG | SANDBOX_TEST |
| `/api/alpha/url-review` | `alpha-url-review.mjs` | URL review via Firecrawl | SANDBOX_TEST |
| `/api/alpha/*` | `alpha-provider.mjs` | LLM provider proxy | SANDBOX_TEST |

---

## Supabase Edge Function Routes

| Function | Purpose | Status |
|----------|---------|--------|
| `hermes-chat` | LLM chat proxy | SANDBOX_TEST |
| `hermes-search` | Web search proxy | SANDBOX_TEST |

---

## Static Routes

| Route | Purpose | Status |
|-------|---------|--------|
| `/got-funding` | Got Funding landing page | APPROVED_LIVE |
| `/got-funding/index.html` | Got Funding static page | APPROVED_LIVE |

---

## Key Finding

The UI has **27 routes** (9 client + 16 admin tabs + 2 top-level). All admin tabs and client portal pages show **mock/placeholder data**. Only Got Funding and auth routes are live. The route structure is solid but data connections are missing.

---

## Recommendation for Prompt 2

1. Keep all routes (structure is good)
2. Replace mock data in top 5 most-used tabs first
3. Add loading states and error handling
4. Connect to live Supabase data
5. Add "last updated" timestamps
