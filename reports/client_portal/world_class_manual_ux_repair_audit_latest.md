# World-Class Manual UX Repair Audit

- Starting commit: `e249b16`
- Current world-class design remains active: `True`
- Old client portal design restored: `False`
- Hero image preserved: `/assets/client-portal/nexus-funding-path-hero.png`

## Findings

- Credit Health overlap came from a desktop page host with hidden overflow plus a fixed four-row `.wc-panel-credit` grid after the page gained five content bands.
- Credit Health dead/weak actions included static `View all` labels, non-action factor cards, top-next-move text spans, and a generic document view button.
- `Chat with Clyde` routed directly to `/client/resources`, which made chat behave like navigation instead of assistance.
- Icon sizing was still close to the downloaded preview sizing: nav icons around `30px`, soft/card icons around `44px`, upload icons around `60px`, and Clyde around `64px`.
- `/client/dispute-review` was explicitly special-cased in `ClientPortalRoot.jsx` to render the old `ClientPortalShell` and `ClientPortalPages` route map.

## Repair Plan

- Keep `WorldClassClientPortal.jsx` and `world-class-client-portal.css` as the active design.
- Let dense portal pages scroll in normal document flow and expand Credit Health grid rows.
- Wire Credit Health upload, resources, factor, guidance, and funding-readiness actions.
- Replace the default Clyde resource redirect with an in-page Clyde drawer.
- Route `/client/dispute-review` through the world-class portal and add a premium dispute-review panel that reuses live credit repair / DocuPost helpers.
- Increase icon sizes with scoped CSS overrides while preserving the premium shell.
