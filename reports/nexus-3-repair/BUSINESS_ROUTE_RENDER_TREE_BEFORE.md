# Business Route Render Tree Before

Date: 2026-07-18

Routes inspected: `/client/business-journey`, `/client/business-setup`, `/client/business-bankability`, `/client/business-credit`

```text
WorldClassClientPortal
└── .wc-pageHost
    ├── FundingReadinessHeader
    ├── ClientRevenueServiceCard
    ├── GuidedClientJourneySurface
    │   └── routeKey="business"
    │       ├── business foundation StageCard
    │       └── business bankability StageCard
    └── BusinessPanel
        ├── Hero variant="business"
        ├── SectionTabs
        └── Business workspace content
```

Result before repair: the approved Business workspace was also inserted after shared legacy/guided route chrome.
