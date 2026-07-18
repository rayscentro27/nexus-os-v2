# Credit Route Render Tree Before

Date: 2026-07-18

Repository checkpoint: `a2c3227e1995ecbf4a719910fbe9e9ad47e0a529`

Route inspected: `/client/credit-profile`

## Render Tree

```text
WorldClassClientPortal
└── .wc-client-portal
    ├── .wc-sidebar
    ├── .wc-main
    │   ├── .wc-topbar
    │   └── .wc-pageHost
    │       ├── FundingReadinessHeader
    │       ├── ClientRevenueServiceCard
    │       ├── GuidedClientJourneySurface
    │       │   └── routeKey="credit"
    │       │       ├── StageCard / readiness contribution surface
    │       │       └── Credit stage guidance
    │       └── CreditPanel
    │           ├── Hero variant="credit"
    │           ├── SectionTabs
    │           ├── Credit Profile Overview
    │           ├── report upload actions
    │           ├── strategy cards
    │           └── Credit Repair case engine
    ├── ClydePanel
    ├── ClydeChatDrawer
    └── SimpleDocumentUploadPanel
```

## Incorrect Visible Blocks

| Block | Source | Result |
|---|---|---|
| Dark Funding Readiness / Credit progress header | `FundingReadinessHeader` rendered unconditionally by `WorldClassClientPortal` | Appears above the approved Credit workspace |
| Purchased service card | `ClientRevenueServiceCard` rendered unconditionally by `WorldClassClientPortal` | Appears above the approved Credit workspace |
| Legacy guided Credit checklist/contribution surface | `GuidedClientJourneySurface routeKey="credit"` rendered unconditionally by `WorldClassClientPortal` | Stacks legacy readiness guidance above the approved Credit design |
| Approved Nexus 3.0 Credit workspace | `CreditPanel` | Correct component, but inserted after legacy wrappers |

## Root Cause

`WorldClassClientPortal` renders three shared journey/service components inside `.wc-pageHost` before the active route panel for every route. The Nexus 3.0 Credit implementation was added as `CreditPanel`, but the route still inherited the legacy wrapper content. This made the approved design additive instead of replacing the visible page.

## Required Repair

`/client/credit-profile` must render the shared application shell once, then the `CreditPanel` workspace as the complete center-column experience. The shared legacy journey/service components must not wrap or precede the Credit route.
