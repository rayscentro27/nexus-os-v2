# Client Portal React Conversion Report

**Generated:** 2026-07-05  
**Status:** Active Build  

## Existing Shell Analysis

- `ClientPortalShell.jsx` provides base layout with header, sidebar, content area
- Current routes: `/portal/dashboard`, `/portal/documents`, `/portal/score`, `/portal/funding`, `/portal/settings`
- Missing routes: `/portal/onboarding`, `/portal/grants`, `/portal/team`, `/portal/billing`, `/portal/support`

## Journey Steps Coverage

| Step | Status | Notes |
|------|--------|-------|
| 1. Onboarding | Missing | Needs wizard component |
| 2. Credit Score | Implemented | Score display + factors |
| 3. Document Vault | Implemented | Upload/list view |
| 4. Business Setup | Missing | EIN, LLC, entity flow |
| 5. Funding Readiness | Implemented | Dashboard metric |
| 6. Funding Applications | Partial | List only, no detail view |
| 7. Grant Discovery | Missing | Search + apply flow |
| 8. Team Access | Missing | Role-based invites |
| 9. Billing/Subscription | Missing | Stripe integration point |
| 10. Support/Help | Missing | FAQ + ticket system |

## Premium Design Target

Benchmark: Got Funding platform aesthetic - clean, professional, trust-building.

Key elements:
- Minimal chrome, generous whitespace
- Consistent type scale (14/16/20/24px)
- Card-based layouts with subtle shadows
- Status indicators (green/yellow/red dots)
- Progress bars for journey completion

## Component Inventory

```
src/components/portal/
├── ClientPortalShell.jsx        (existing, refactor)
├── PortalHeader.jsx             (new)
├── PortalSidebar.jsx            (new, collapsible)
├── PortalDashboard.jsx          (new)
├── OnboardingWizard.jsx         (new)
├── CreditScoreCard.jsx          (refactor from existing)
├── DocumentVault.jsx            (refactor)
├── FundingTracker.jsx           (new)
├── GrantDiscovery.jsx           (new)
├── TeamManagement.jsx           (new)
├── BillingSettings.jsx          (new)
├── SupportCenter.jsx            (new)
└── PortalSettings.jsx           (refactor)
```

## Data Adapter

`clientPortalDataAdapter.ts` created - see separate adapter report.

## No-Scroll Desktop Layout

See separate no-scroll desktop report.

## Next Build Tasks

1. **Priority 1:** Refactor `ClientPortalShell.jsx` into component architecture
2. **Priority 2:** Build `PortalHeader.jsx` + `PortalSidebar.jsx`
3. **Priority 3:** Implement route structure (9 new routes)
4. **Priority 4:** Build `OnboardingWizard.jsx` (step 1 missing)
5. **Priority 5:** Build `GrantDiscovery.jsx` + `TeamManagement.jsx`
6. **Priority 6:** Stripe billing integration points
7. **Priority 7:** Mobile responsive pass
8. **Priority 8:** Premium design polish (Got Funding benchmark)
