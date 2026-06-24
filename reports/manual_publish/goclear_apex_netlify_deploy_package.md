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
2. If using CLI, run: netlify login.
3. Run: netlify init, choose this GitHub repo, set build command npm run build, and publish directory dist.
4. Or set NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID in local runtime env.
5. Deploy with: netlify deploy --prod --dir=dist.
6. Open the deployed site at /goclear-apex-readiness.html.
7. Optionally add NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID locally for future CLI deploy checks.

No public URL is claimed until Netlify is connected or a manual deploy completes.
