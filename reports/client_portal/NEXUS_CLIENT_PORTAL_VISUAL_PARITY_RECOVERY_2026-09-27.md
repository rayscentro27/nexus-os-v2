# Nexus Client Portal Visual Parity Recovery — 2026-09-27

VISUAL_DRIFT_ROOT_CAUSE=The approved portal CSS was imported into the global document and then collided with later Nexus Tailwind v3 output and legacy global rules. Shared utility names such as `.hidden`, `.grid`, `.grid-cols-2`, and responsive variants were therefore resolved by the host cascade; at 1440x900 the approved `aside` became `display:none`, the 7-step journey became two columns, and the mission grid expanded across the viewport.

TAILWIND_STRATEGY=Keep Nexus Tailwind v3 unchanged. Preserve the approved static bundle and generate a namespaced copy with a small PostCSS script.

CSS_ISOLATION_METHOD=Wrap the approved application in `.goclear-approved-portal`, scope the generated utility bundle to that root, and scope portal theme variables/resets/animations. The live Nexus bridge remains the data/action boundary.

FILES_CHANGED=src/client-v2/approved/ApprovedClientPortal.tsx; src/client-v2/approved/portal-theme.css; src/client-v2/approved/generated.scoped.css; scripts/namespace-approved-portal-css.mjs; tests/e2e/client_portal_visual_parity.spec.ts; docs/architecture/NEXUS_GOOGLE_AI_STUDIO_VISUAL_ISOLATION_STANDARD_V1.md; docs/design/NEXUS_ADMIN_GOOGLE_AI_STUDIO_INTEGRATION_PREFLIGHT.md; package.json; package-lock.json; playwright.config.ts; this report; JSON report.

TYPECHECK=PASS — `npx tsc --noEmit`
BUILD=PASS — `npm run build` (existing chunk-size and dynamic-import warnings only)
FOCUSED_TESTS=PASS — Playwright visual structure smoke: 2 passed (desktop and mobile). The test runner dependency and executable-path fallback were added because the canonical package did not declare `@playwright/test` and this macOS environment cannot download the newest bundled Chromium.
DESKTOP_LOCAL=PASS — local preview captured at 1440x900; sidebar flex/visible, journey 7 columns, mission grid 2 columns, Momentum present, footer flex/visible.
DESKTOP_PRODUCTION=PASS — post-deploy production preview at 1440x900 reports approved root present, sidebar flex at 256px, 7-column journey, and 2-column mission grid.
MOBILE=PASS — 390x844 captured; desktop aside hidden and Mobile Navigation Dock visible.
AUTH_LIVE=NOT_INSPECTED — no safe authenticated production session was available in this run; live bridge wiring was not changed.
VISUAL_PARITY=PASS — local and production rendered structure match the approved component geometry; dynamic data values remain allowed to differ.
CLIENT_DATA_BINDING=PASS — `installNexusPortalBridge()` and approved context data/action paths are unchanged.
GLOBAL_NEXUS_UI_REGRESSION=PASS — change is root-scoped; typecheck/build pass and no global Nexus stylesheet was upgraded.
ADMIN_INTEGRATION_STANDARD_CREATED=PASS

COMMITS_CREATED=4ecac452; 95067c95; f4632bdd
COMMITS_PUSHED=PASS — `main` pushed to `origin` at f4632bdd
NETLIFY_DEPLOYMENT=PASS — existing Netlify Git deployment rolled out and production re-verified at https://goclearonline.cc/client/preview

Evidence screenshots are in `reports/client_portal/visual-baseline/`.
