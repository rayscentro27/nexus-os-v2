# Selective Commit Plan

## Commit 1

Message:
- `complete nexus 3 authenticated workflow certification repairs`

Files staged:
- `src/pages/client/WorldClassClientPortal.jsx` - mobile/tablet Hermes launcher and reachable top-bar sign-out.
- `src/styles/world-class-client-portal.css` - responsive launcher, top-bar sign-out, scrollable sidebar styling.
- `src/components/ClientsPanel.jsx` - hook-order repair and stable admin workflow selectors.
- `tests/e2e/nexus3-final-authenticated-certification.spec.ts` - authenticated final client/admin/responsive/accessibility regression.

Security/privacy:
- No secrets.
- No PII.
- No document contents.
- No browser auth state.

## Commit 2

Message:
- `document nexus 3 final authenticated certification`

Files staged:
- sanitized reports under `reports/nexus-3-final/`.

Excluded:
- `.env*`
- `test-results/`
- runtime/cache
- Telegram
- Alpha
- trading
- work-order artifacts
- unrelated reports
- temporary files
