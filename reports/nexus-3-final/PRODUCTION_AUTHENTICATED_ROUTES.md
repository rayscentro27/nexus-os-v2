# Production Authenticated Routes

Production URL: https://goclearonline.cc

Result: PASS

Production bundle evidence:
- Production HTML served a bundle containing `wc-mobileHermesLauncher`.
- Production HTML served a bundle containing `wc-topSignOut`.
- Production HTML served a bundle containing `admin-client-detail-drawer`.
- Production HTML served a bundle containing `admin-client-list`.

Authenticated routes certified through Playwright against production:
- /client/dashboard
- /client/credit-profile
- /client/credit-utilization
- /client/account-details
- /client/credit-repair-journey
- /client/business-journey
- /client/business-setup
- /client/business-bankability
- /client/business-credit
- /client/documents
- /client/funding-readiness
- /client/recommendations
- /client/resources
- /client/request-review
- /admin
- /admin#clients
- /admin#readiness-admin

Legacy stacking result: PASS. No active client route panel rendered the old purchased-service/guided wrapper above the Nexus 3 workspace.
