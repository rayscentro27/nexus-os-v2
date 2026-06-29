# Client Portal Prototype Integration Plan

- Admin entry: `src/main.tsx` → `src/app/App.tsx` → authenticated `NexusAdminUI`.
- Current navigation: internal React state; React Router is not installed.
- Current auth: Supabase session gate for the admin app; role-specific client routing is not complete.
- Admin mount: `/` and all non-client paths remain behind `AuthGate`.
- Client mount: `src/app/App.tsx` will route `/client` and `/client/*` to a separate client shell without changing the admin shell.
- Client preview access: direct during this prototype integration; data is static/demo-only.
- Admin bridge: add a visible `View Client Portal` link to the admin topbar.
- Browser navigation: use pathname/history handling with no new package installation.
- Safety: Hermes remains admin-only. Nexus Guide receives only approved, client-visible static data.

## Activation Plan

1. Extract and inventory the local ZIP without network access.
2. Adapt the prototype shell, score cards, progress rings, factors, tables, and premium dark style.
3. Complete all nine client child routes, including Documents, Messages, and Settings.
4. Generate static repo concepts and Supabase-ready client workflow records.
5. Connect Hermes/Ray Review to Nexus Guide through structured approval records.
6. Build, preview, route-test, and run local safety scans.
