# WP8.14D Operator Finance visual E2E

Existing synthetic operator credentials from `.env.e2e.local` authenticated successfully against `/admin/login`. The Playwright test opened `/operator/finance`, verified campaign/trading/resource content and no horizontal overflow, and captured authenticated 1440x1000 desktop and 390x844 mobile screenshots. Both isolated tests passed.

The first desktop capture exposed a truncated stylesheet from an earlier Finance change. The last known-good Operator stylesheet was restored and Finance styles were appended; rerendered screenshots are the evidence used for certification.
