# Client Portal Action Map — Nexus OS v2

## Navigation Actions (Shell Sidebar)

| Label | Route | Component | Action Type | Status |
|-------|-------|-----------|-------------|--------|
| Home | `/client/dashboard` | `ClientDashboard` | navigation | active |
| Credit Profile | `/client/credit-profile` | `CreditProfilePage` | navigation | active |
| Credit Utilization | `/client/credit-utilization` | `CreditUtilizationPage` | navigation | active |
| Documents | `/client/documents` | `ClientDocumentsPage` | navigation | active |
| Business Setup | `/client/business-setup` | `BusinessSetupPage` | navigation | active |
| Business Bankability | `/client/business-bankability` | `BusinessBankabilityPage` | navigation | active |
| Funding Readiness | `/client/funding-readiness` | `FundingReadinessPage` | navigation | active |
| Recommendations | `/client/recommendations` | `RecommendationsPage` | navigation | active |
| Resources | `/client/resources` | `ResourcesPage` | navigation | active |
| Request Review | `/client/request-review` | `RequestReviewPage` | navigation | active |
| Sign Out | — | `supabase.auth.signOut()` | auth/write | active |

## Header Icon Actions

| Label | Route | Action Type | Status | Notes |
|-------|-------|-------------|--------|-------|
| Notifications (🔔) | `/client/resources` | navigation | active | **MISROUTED** — should go to notifications page |
| Messages (✉) | `/client/resources` | navigation | active | **MISROUTED** — should go to `/client/messages` |
| Help (❓) | `/client/resources` | navigation | active | **MISROUTED** — should go to help/support |
| Menu (☰) | — | toggle mobile sidebar | hidden | `display: 'none'` — unreachable |

## Dashboard Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Upload Now | `/client/documents` | navigation | none | active |
| Improve Approval Odds | `/client/credit-utilization` | navigation | none | active |
| Funding Journey tiles | Various | navigation | none | active |
| Quick link cards | Various | navigation | none | active |
| Recommended tool links | Various | navigation | none | active |

## Credit Profile Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Connect Monitoring | `/client/resources` | navigation | none | active |
| Upload Report | `/client/documents` | navigation | none | active |
| Free Report Options | `/client/resources` | navigation | none | active |

## Credit Utilization Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Recommended actions (4) | Per-action `_route` | navigation | none | active |

## Document Actions

| Label | Route | Action Type | Data Write | Admin Visibility | Status |
|-------|-------|-------------|------------|-----------------|--------|
| Upload zone | — | upload | Storage + metadata insert | Creates `pending_review` row | active (gated) |
| Remove file (×) | — | upload/management | none | none | active (pending only) |
| Uploaded Documents card | `/client/documents` | navigation | none | none | active |
| Signed Forms card | `/client/documents` | navigation | none | none | active |
| Credit Reports card | `/client/documents` | navigation | none | none | active |

## Business Setup Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Open Online Bank Account | `/client/business-bankability` | navigation | none | active |
| Add Existing Account | `/client/business-bankability` | navigation | none | active |
| Relationship Bank | `/client/business-bankability` | navigation | none | active |
| Recommended Providers | Various | navigation | none | active |

## Business Bankability Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Recommended banks (3) | `/client/resources` | navigation | none | active |

## Funding Readiness Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Top Blocker tiles | Various | navigation | none | active |
| Next Best Action items | Various | navigation | none | active |
| Recommended Tool links | Various | navigation | none | active |

## Recommendations Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Matched opportunities | `/client/recommendations` | navigation | none | active |
| Funding paths | `/client/funding-readiness` | navigation | none | active |
| Partner/tool options | `/client/resources` | navigation | none | active |

## Resources Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Credit Monitoring items | Various | navigation | none | active |
| Mailing Options items | `/client/documents` | navigation | none | active |
| Business Banking items | `/client/business-bankability` | navigation | none | active |
| Credit Report Upload items | Various | navigation | none | active |

## Request Review Actions (★ CRITICAL WRITE)

| Label | Route | Action Type | Data Write | Admin Visibility | Status |
|-------|-------|-------------|------------|-----------------|--------|
| **Request Review** | `handleSubmitReview()` | write | `client_tasks.insert()` with `category='review_request'`, `status='pending_admin_review'` | Creates admin-visible review request | gated (requires no open high-priority tasks) |

## Messages Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| (no buttons) | — | read-only | none | FALLBACK (read-only preview) |

## Settings Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| (no buttons) | — | read-only | none | FALLBACK (read-only preview) |

## Guide Panel Actions

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Guidance chip buttons | — | help | none | active |
| Ask input submit | — | help | none | active |

## Admin Actions (NexusAdminUI)

| Label | Route | Action Type | Data Write | Status |
|-------|-------|-------------|------------|--------|
| Sidebar nav (20+ items) | Hash routes | navigation | none | active |
| Approve | — | write | Local receipt state | active |
| Hold | — | write | Local receipt state | active |
| Ask Hermes | — | navigation | none | active |
| Save Note | — | write | Local state | active |
| Copy command | — | clipboard | none | active |
| Create dry-run publish job | — | write | `approvals` insert | active |
| Queue creative job | — | write | `agent_jobs` insert | active |

## Write Action Summary

| Write Target | Trigger | Tables | Status |
|--------------|---------|--------|--------|
| Document upload | File drop/select | `storage.objects` + `client_documents` | LIVE |
| Request Review | Button click | `client_tasks` | LIVE |
| Admin Approve/Hold | Button click | Local state only | active |
| Admin Save Note | Button click | Local state only | active |
| Admin queue jobs | Various | `agent_jobs`, `approvals` | active |

## Missing/Broken Actions

| Issue | File | Impact |
|--------|------|--------|
| `src/clientPortal/clientActions.ts` missing | — | Import failures if referenced |
| `/client/preview` references missing `ClientPreviewPage` | `App.tsx` | 404/blank page |
| Header icon buttons misrouted to `/client/resources` | `ClientPortalShell.jsx` | Poor UX |
| Mobile menu toggle hidden | `ClientPortalShell.jsx` | Mobile sidebar unreachable |
| Messages badge hardcoded to "2" | `ClientPortalShell.jsx` | Stale count |
