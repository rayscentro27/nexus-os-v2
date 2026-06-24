# GoClear/Apex Landing Page Deploy Package

- Status: deploy_ready_manual_netlify_required
- Source: `public/goclear-apex-readiness.html`
- Built file: `dist/goclear-apex-readiness.html`
- Public path after deploy: `/goclear-apex-readiness.html`
- Missing Netlify env names: NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID

## Netlify Settings
- Build command: `npm run build`
- Publish directory: `dist`
- Landing page path: `/goclear-apex-readiness.html`

## Manual Steps
1. Run npm run build.
2. In Netlify, create or open the site connected to this GitHub repo.
3. Use build command: npm run build.
4. Use publish directory: dist.
5. Deploy main, then open /goclear-apex-readiness.html.
6. Optionally add NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID locally for future CLI deploy checks.

No public URL is claimed until Netlify is connected or a manual deploy completes.
