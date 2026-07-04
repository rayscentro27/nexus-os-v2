# Got Funding Custom-Domain Route Fix

- Added Vite development middleware for `/got-funding` and `/got-funding/`.
- Preserved direct `/got-funding/index.html` static serving.
- Added explicit Netlify rewrites before the Nexus SPA fallback.
- Added `/got-funding.html` backup/canonical redirect.
- Build output contains `dist/got-funding/index.html`, QR SVG/PNG, and print-test HTML.
- SPA hash routes remain covered by the final catch-all.
- Read-only public checks returned the teaser title at `goclearonline.cc`, its `www` redirect, and the Netlify fallback.
