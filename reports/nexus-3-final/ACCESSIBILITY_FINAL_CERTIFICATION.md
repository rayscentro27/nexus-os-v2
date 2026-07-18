# Accessibility Final Certification

Result: PASS for automated targeted checks; PARTIAL for full axe coverage because no axe dependency is installed.

Checks performed through Playwright:
- buttons have accessible names;
- non-decorative images have alt attributes;
- primary route headings exist;
- key authenticated routes are keyboard/action reachable;
- Hermes drawer has dialog role and close control;
- upload and admin controls expose visible or programmatic names.

Repairs:
- Added a visible top-bar sign-out control for reliable account exit.
- Added a tablet/mobile Hermes launcher with accessible name and decorative hidden image.

Remaining noncritical issue:
- Full axe scan was not run because `@axe-core/playwright` is not installed.
