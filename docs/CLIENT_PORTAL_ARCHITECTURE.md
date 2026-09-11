# Client portal architecture boundary

`src/pages/client/WorldClassClientPortal.jsx` and the legacy `/client/*`
presentation are frozen for maintenance and bug fixes only. New client-facing
features must be implemented in the isolated V2 tree under
`src/client-v2/`, routed through `/client-v2/*` and its existing authenticated
gate. Production `/client` routing is intentionally not cut over by R30A.

R30A uses the proven Supabase/Auth/RLS, readiness, documents, funding-gate,
Clyde, Customer Service, communications, and entitlement contracts. V2 page
responsibilities remain separate: dashboard summary, credit, utilization,
documents, business, bankability, funding readiness, recommendations,
resources, review, support, account, and contextual Clyde. A page must expose
`REAL_BACKEND_CONNECTED` truthfully; visual placeholders are not live state.

The existing V2 shell, responsive primitives, live data hook, and route map
are the greenfield foundation. No legacy giant-page component may be imported
into a new V2 feature by default.
