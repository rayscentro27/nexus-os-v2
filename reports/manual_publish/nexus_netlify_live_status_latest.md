# Nexus — Netlify Live Deployment Status

- generated_at: 2026-06-24 (GitHub-connected detection update)
- repo: ~/nexus-os-v2 · branch main
- build: PASS (`tsc --noEmit && vite build`) · watch: PASS (`npm run nexus:watch`, 0 errors, no email/post/trade)
- deploy path: **push `main` → Netlify build/deploy** (settings now self-documented in `netlify.toml`).

> Live "latest" copy: gitignored `reports/runtime/nexus_netlify_live_status_latest.md`.
> Committed copy (this file): tracked `reports/manual_publish/`.

---

## What changed
- **Added `netlify.toml`** (repo root): build command `npm run build`, publish dir `dist`, SPA
  fallback redirect `/* → /index.html 200`. Build settings now agree between repo and dashboard.
- **Improved Nexus Netlify detection** so a GitHub-connected deploy is tracked **without** local
  Netlify CLI tokens:
  - Existing `NETLIFY_AUTH_TOKEN` / `NETLIFY_SITE_ID` detection is kept (now reported as
    `cli_capable`, used only for optional CLI/API verification).
  - New public-URL config: `NEXUS_NETLIFY_PUBLIC_URL` (or `VITE_GOCLEAR_PUBLIC_URL`).
  - New classification fields: `deploy_mode`, `public_url`, `status`, `blocker`.

## Current detection result (this run)
```
netlify: connected=unknown deploy_mode=github_connected_assumed public_url=none
         cli_capable=False netlify_toml=True
landing status: github_connected_assumed_provide_public_url
```
This is correct: Netlify is connected via GitHub (netlify.toml present), and the only missing piece
is the **public URL**, which Nexus cannot know until it's provided. Nexus no longer falsely claims
"manual deploy required" and no longer treats the missing CLI token as a blocker.

## Classification logic (how Nexus now reports Netlify)
| Condition | connected | deploy_mode | status | blocker |
|---|---|---|---|---|
| Public URL provided | `true` | `github_connected_public_url` | `public_url_configured_needs_live_verification` | none |
| No URL, but `netlify.toml` or CLI creds present | `unknown` | `github_connected_assumed` | `github_connected_assumed_no_public_url` | `missing_public_url_in_repo_or_env` |
| Nothing configured | `false` | `not_configured` | `not_configured` | `missing_public_url_in_repo_or_env` |

Nexus will **not** claim the landing page is live until a public URL is provided (and ideally
verified loading).

## Required env / config
- **For the GitHub build (set in the Netlify UI):** `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`,
  `VITE_HERMES_CHAT_ENABLED=true`. (Provider keys stay in Supabase secrets, never in Netlify.)
- **For Nexus status tracking (local/runtime):** `NEXUS_NETLIFY_PUBLIC_URL` = the public site URL.
- **Not needed for the GitHub deploy:** `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` — CLI/API
  verification only.

## Money-readiness
- **Landing page:** built (`dist/goclear-apex-readiness.html`) and deployable via GitHub; becomes
  money-capable the moment the public URL is confirmed (email-CTA intake works to start).
- **Resend follow-up:** ready to point at `<public-url>/goclear-apex-readiness.html`.
- **Facebook one-post approval (`13eafcab`):** ready to link to `<public-url>/goclear-apex-readiness.html`
  once approved + `publish_enabled=true` (keep the one-post limit).

## Remaining blocker
- **The public Netlify domain/URL.** Provide it via `NEXUS_NETLIFY_PUBLIC_URL` (or
  `VITE_GOCLEAR_PUBLIC_URL`), or paste it to me, and Nexus will flip to
  `public_url_configured_needs_live_verification` and the deploy package will print the live page URL.
- `$97` intake is still email-CTA only (fine to start; real form/checkout needed before paid traffic).

## Next recommended action (exactly one)
**Provide the public Netlify URL** — set `NEXUS_NETLIFY_PUBLIC_URL=https://<your-netlify-domain>` in
local `.env` (and the matching `VITE_*` Supabase vars in the Netlify UI). Then `npm run nexus:watch`
will report `deploy_mode=github_connected_public_url` and the live page at
`https://<your-netlify-domain>/goclear-apex-readiness.html`, which Resend and the Facebook test post
can point to.

(Do not manual-deploy — GitHub is the deploy path. Manual `netlify deploy` only if the GitHub deploy
fails.)
