# Selective Commit Plan

## Files to Stage

| File | Purpose | Sensitive |
|---|---|---|
| `src/pages/client/WorldClassClientPortal.jsx` | Remove legacy route wrapper, tabs-first Credit/Business, add dedicated Recommendations panel | No |
| `src/styles/world-class-client-portal.css` | Fix hero overlay click interception and style Recommendations panel | No |
| `tests/nexus3_route_replacement.test.ts` | Static regression preventing legacy/new route stacking | No |
| `reports/nexus-3-repair/*.md` | Sanitized certification reports | No |
| `reports/nexus-3-repair/nexus_3_replacement_manifest.json` | Sanitized manifest | No |

## Explicitly Excluded

- runtime/cache files;
- Alpha artifacts;
- Telegram artifacts;
- trading artifacts;
- local credentials;
- browser auth state;
- temporary screenshots;
- unrelated reports;
- customer documents;
- customer PII.

Staging command must use explicit paths only.
