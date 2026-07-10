# Button Action Map Fixes

## Fixes Applied

1. `src/pages/client/WorldClassClientPortal.jsx`
   - Resources cards now use contextual routes through `routeForResource(...)`.
   - Partner/resource cards now route to relevant request-review fallback topics when no approved external URL is configured.
   - Notification bell is disabled/gated with explanatory title instead of routing to Resources.
   - User/avatar pill now routes to `/client/profile`.

2. `src/lib/creditReportReviewFlow.ts`
   - Manual negative item now routes to `/client/credit-repair-journey?action=manual-negative-item`.

## Fixes Not Applied

- No parser/OCR was added.
- No external partner URLs were invented.
- No new credit bureau connection was added.
- No DocuPost gate was weakened.
