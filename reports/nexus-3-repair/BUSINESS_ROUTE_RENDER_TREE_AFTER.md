# Business Route Render Tree After

Date: 2026-07-18

Routes inspected: `/client/business-journey`, `/client/business-setup`, `/client/business-bankability`, `/client/business-credit`

```text
WorldClassClientPortal
└── .wc-pageHost
    └── BusinessPanel
        ├── SectionTabs
        ├── Hero variant="business"
        └── Business workspace content
```

Result: Business routes now render the approved Business workspace directly. Shared legacy/guided blocks no longer stack above the Business page.
