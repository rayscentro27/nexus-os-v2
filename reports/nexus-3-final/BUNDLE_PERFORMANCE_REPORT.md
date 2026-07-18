# Bundle Performance Report

Result: PASS with noncritical follow-up.

Production build:
- Command: `npm run build`
- Exit code: 0
- JS bundle: `dist/assets/index-eeptzk9B.js` at 1,552.75 kB, gzip 390.55 kB
- CSS bundle: `dist/assets/index-DcB-Ll14.css` at 145.41 kB, gzip 27.80 kB
- Largest image assets: approved Credit/Business/Hermes assets from Nexus 3 design package.

Warning:
- Vite emitted a chunk-size warning for the main bundle.

Decision:
- Noncritical for controlled client testing. Route-level splitting of admin/client and heavier workbench tools should be scheduled after Nexus 3 final certification.
