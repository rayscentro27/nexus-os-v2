# GoClear/Apex Landing Page Deploy Package

- Status: github_connected_assumed_provide_public_url
- Deploy mode: github_connected_assumed
- Public URL: not provided yet (set NEXUS_NETLIFY_PUBLIC_URL or VITE_GOCLEAR_PUBLIC_URL)
- Public landing page: pending public URL
- Source: `public/goclear-apex-readiness.html`
- Built file: `dist/goclear-apex-readiness.html`
- Public path after deploy: `/goclear-apex-readiness.html`
- netlify.toml present: True

## Netlify Settings (self-documented in netlify.toml)
- Build command: `npm run build`
- Publish directory: `dist`
- Landing page path: `/goclear-apex-readiness.html`
- GitHub-connected deploy does NOT need NETLIFY_AUTH_TOKEN / NETLIFY_SITE_ID.

## Steps
1. Preferred: push main to GitHub; Netlify builds and deploys automatically (netlify.toml present).
2. Provide the public URL to Nexus by setting NEXUS_NETLIFY_PUBLIC_URL (or VITE_GOCLEAR_PUBLIC_URL).
3. CLI/API verification (optional): set NETLIFY_AUTH_TOKEN and NETLIFY_SITE_ID locally.
4. Manual deploy is only needed if the GitHub-connected deploy fails: netlify deploy --prod --dir=dist.

No public URL is claimed live until the URL is configured (and verified).
