# Credit Route Render Tree After

Date: 2026-07-18

Route: `/client/credit-profile`

```text
WorldClassClientPortal
└── .wc-client-portal
    ├── .wc-sidebar
    ├── .wc-main
    │   ├── .wc-topbar
    │   └── .wc-pageHost
    │       └── CreditPanel
    │           ├── SectionTabs
    │           ├── Hero variant="credit"
    │           ├── Credit Profile Overview
    │           ├── report upload actions
    │           ├── strategy cards
    │           └── Credit Repair case engine
    ├── ClydePanel
    ├── ClydeChatDrawer
    └── SimpleDocumentUploadPanel
```

Result: the route now renders one route-owned Credit workspace. The legacy `FundingReadinessHeader`, `ClientRevenueServiceCard`, and `GuidedClientJourneySurface` no longer wrap or precede the Credit panel.
