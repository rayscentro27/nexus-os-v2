# WP8.12 Operator Browser E2E

Authenticated Playwright certification passed three scenarios: login → `/operator` Home → `/operator/creative`; desktop baseline capture; and mobile Home/Creative capture. The Creative route rendered five real cards, loaded remote-backed previews, selected the real video card, opened comparison, and exercised approve/request-revision/reject UI states without publication.

`OPERATOR_BROWSER_E2E=PASS`; `REAL_BROWSER_SCREENSHOTS_USED=YES`. Browser action UI state is proven; durable receipt persistence remains owned by the existing backend review path and was not rewritten in this migration.
