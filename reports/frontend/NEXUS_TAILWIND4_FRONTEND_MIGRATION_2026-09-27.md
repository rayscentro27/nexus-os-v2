# Nexus Tailwind 4 Frontend Migration — 2026-09-27

## Result

`TAILWIND4_MIGRATION=PASS`

The Nexus frontend now uses Tailwind CSS 4.3.3 through the official Vite integration. The approved GoClear Client Portal is generated from its approved source with Tailwind 4 CLI output and a scoped visual boundary. Nexus live data, authentication, routing, actions, and Clyde integration remain in place.

## Migration identity

- `MIGRATION_WORKTREE=/Users/raymonddavis/nexus-os-v2-tailwind4`
- `MIGRATION_BRANCH=migration/tailwind4-frontend`
- `BASE_SHA=bc656ba21e8e0ca96270d7fcef26b106d7f725a8`
- `PRE_MIGRATION_PRODUCTION_SHA=bc656ba21e8e0ca96270d7fcef26b106d7f725a8`
- Previous Tailwind: `3.4.19`
- New Tailwind: `4.3.3`
- Vite: `5.4.21`
- PostCSS: `8.5.26` retained for existing tooling; Tailwind application integration is Vite-native.

## Root cause

`VISUAL_DRIFT_ROOT_CAUSE=` The approved portal was being rendered in a Tailwind 3 host while its approved utility source expected modern Tailwind behavior. The old generated compatibility bundle did not reliably provide the approved v4 utility set, including the desktop sidebar width utility. In addition, the host stylesheet contained unlayered legacy selectors such as `.grid` and `.hidden`. Tailwind 4 utility rules emitted inside `@layer utilities` therefore lost the cascade against those host rules even when the utility class was present. The result was a 256px sidebar, collapsed readiness journey, and incorrect mission-grid geometry. This was verified by removing the scoped bundle and observing the collapse, then restoring the bundle with namespace scoping and flattened internal layers.

## Tailwind strategy

`TAILWIND_STRATEGY=` Tailwind 4.3.3 is the canonical Nexus frontend foundation. `@tailwindcss/vite` is installed in `vite.config.ts`, the global CSS entry uses `@import "tailwindcss"` and CSS-first `@theme`, and the approved portal uses `@tailwindcss/cli` with `@import "tailwindcss" source("./")` to create a package-local static bundle. Nexus was not globally reverted to Tailwind 3 and was not manually redesigned utility-by-utility.

`TAILWIND4_INTEGRATION_METHOD=@tailwindcss/vite application integration + @tailwindcss/cli package-local approved portal bundle`

## Isolation and compatibility decisions

`CSS_ISOLATION_METHOD=` Approved CSS is generated from `src/client-v2/approved/tailwind.v4.css`, namespaced under `.goclear-approved-portal`, and loaded only by the approved portal surface. Its internal Tailwind layers are flattened during namespacing so scoped approved utilities can beat unrelated unlayered host selectors without leaking outside the root.

Removed Tailwind 3 assumptions:

- `tailwind.v2.config.cjs`
- legacy `@tailwind base/components/utilities` source and generated bundle
- old approved generated/index/input CSS files
- `autoprefixer` dependency and the `tailwind:v2` script

Retained intentionally:

- `src/client-v2/approved/generated.scoped.css` — regenerated Tailwind 4 output and the visual boundary
- `scripts/namespace-approved-portal-css.mjs` — package-local namespace generation
- `src/client-v2/approved/portal-theme.css` and `src/client-v2/styles/v2-theme.css` — surface theme and non-utility presentation rules

No unapproved dark/disabled state is rendered by the approved portal; truthful unavailable data remains inside the approved card shell.

## Verification

- `TYPECHECK=PASS` — `npm run typecheck` / `tsc --noEmit`
- `BUILD=PASS` — `npm run build`
- `FOCUSED_TESTS=PASS` — 4 files, 19 tests
- `VISUAL_TESTS=PASS` — 3 Playwright tests locally, plus 3 production route tests
- `DESKTOP_VISUAL_ACCEPTANCE=PASS` — 1440×900 sidebar, command center, 7-column journey, 2-column mission grid, right momentum column, Clyde, and footer metrics
- `MOBILE_VISUAL_ACCEPTANCE=PASS` — 390×844 mobile dock and responsive shell
- `FRONT_PAGE_STATUS=PASS` — public route loads, navigation is visible, and browser smoke reports no page errors
- `CLIENT_PORTAL_NATIVE_TAILWIND4=PASS`
- `CLIENT_PORTAL_VISUAL_PARITY=PASS` — bounded rendered structure/style acceptance; dynamic data is not used as a geometry comparison
- `CLIENT_PORTAL_LIVE_DATA_BINDING=PASS`
- `ADMIN_TAILWIND4_FOUNDATION=PASS` — `src/admin-v2/approved/` and `src/admin-v2/integration/` prepared; Admin UI was not integrated
- `GLOBAL_NEXUS_UI_REGRESSION=PASS` for the exercised public/client routes
- `AUTH_LIVE=NOT_EXERCISED` — no safe authenticated production session was available; live bridge code was preserved and focused live-data tests passed

Evidence is stored under `reports/client_portal/tailwind4-migration/`:

- `client-preview-desktop-1440x900.png`
- `client-preview-mobile-390x844.png`
- `front-page-desktop-1440x900.png`
- `production-client-desktop-1440x900.png`
- `production-client-mobile-390x844.png`
- `production-front-page-desktop-1440x900.png`

## Git and deployment

- `ea1e655f` — `Frontend: migrate Nexus to Tailwind 4`
- `131221ac` — `Client Portal: add Tailwind 4 visual evidence`
- `COMMITS_PUSHED=PASS` — migration branch pushed and fast-forwarded to `origin/main`
- `NETLIFY_DEPLOYMENT=PASS` — production served the migrated bundle after propagation
- `PRODUCTION_CLIENT_PORTAL=PASS`
- `PRODUCTION_FRONT_PAGE=PASS`
- `ROLLBACK_REQUIRED=NO`

The reusable architecture standard and Admin preflight now define Nexus Frontend as Tailwind 4 and require rendered baseline comparison before future Google AI Studio integration.
