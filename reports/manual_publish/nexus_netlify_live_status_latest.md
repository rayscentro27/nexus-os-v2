# Nexus — Netlify Live Deployment Status

- generated_at: 2026-06-24 (verification run)
- repo: ~/nexus-os-v2 · branch main · HEAD a20e885
- build: PASS (`tsc --noEmit && vite build`) · watch: PASS (`npm run nexus:watch`, 0 errors, no email/post/trade)
- update: Netlify is now connected to the GitHub repo. Deploy path = **push to `main` → Netlify build/deploy.**

> Live "latest" copy: gitignored `reports/runtime/nexus_netlify_live_status_latest.md`.
> Committed copy (this file): tracked `reports/manual_publish/`.

---

## Headline finding

**Netlify is connected (GitHub-managed deploy), but Nexus's watch loop does NOT yet recognize it** —
because the watch loop detects Netlify only by **local CLI env names** (`NETLIFY_AUTH_TOKEN`,
`NETLIFY_SITE_ID`), which a GitHub-connected deploy does not use. So the report below shows a **false
negative**; it is a detection gap, not a real blocker.

| Question | Answer |
|---|---|
| Is Netlify connected? | **Yes** — via GitHub (push `main` → Netlify build/deploy), per Ray. |
| Does Nexus think Netlify is blocked? | **Yes (stale)** — watch loop: `netlify connected=False, missing NETLIFY_AUTH_TOKEN, NETLIFY_SITE_ID`; landing `deploy_ready_manual_netlify_required`. This only means *no local CLI deploy creds* — it cannot see the GitHub deploy. |
| Is the landing page public? | **Built & deployable; live status not verifiable from the repo** (no URL stored here). Public once the GitHub deploy ran with publish dir `dist` + VITE envs set. |
| Public URL | **Not in repo config** — it lives in the Netlify dashboard. Path will be `<your-netlify-domain>/goclear-apex-readiness.html`. Provide the domain to finalize verification. |

---

## Build & artifact status
- `npm run build` → PASS. Landing page emits to `dist/goclear-apex-readiness.html` (source
  `public/goclear-apex-readiness.html`, 7.9 KB). Netlify publish dir must be `dist`.
- No `netlify.toml` / `_redirects` committed → Netlify build settings are configured in the Netlify
  UI, not the repo. The **static landing page works without a redirect** (it's a real file at
  `/goclear-apex-readiness.html`); a `/* → /index.html 200` redirect is only needed for the React
  app's client routes.

## Required env vars (set these in the Netlify UI for the GitHub build)
- `VITE_SUPABASE_URL` = `https://iqjwgpnujbeoyaeuwehj.supabase.co`
- `VITE_SUPABASE_ANON_KEY` = (anon key from Supabase dashboard / `.env`)
- `VITE_HERMES_CHAT_ENABLED` = `true`
- (`VITE_HERMES_SEARCH_ENABLED` omit/false — search not deployed)
- **Not needed for the GitHub deploy:** `NETLIFY_AUTH_TOKEN`, `NETLIFY_SITE_ID` (those are only for
  local CLI deploys / for the watch loop to self-verify). Provider keys stay in Supabase secrets —
  never in Netlify.

## Netlify build settings (UI)
- Build command: `npm run build` · Publish directory: `dist` · Node: 20 (Vite 5 needs Node 18+).

---

## Remaining blockers
1. **Verification gap (cosmetic):** the watch loop reports Netlify "blocked" because it checks local
   CLI env only. Real deploy works via GitHub. (Optional later fix: teach the watch loop to accept a
   `NETLIFY_SITE_URL`/site-id, or read a committed `netlify.toml`.)
2. **Live URL not confirmed from here:** repo has no stored URL; confirm the published domain in the
   Netlify dashboard and that the first deploy used publish dir `dist` + the VITE envs.
3. **$97 intake still email-CTA only:** `form_backend: missing_public_form_backend_manual_email_cta_used`
   — fine to start; a real form/checkout backend is needed before paid traffic.

## Money-readiness
- **Landing page: money-capable once the URL is confirmed live** (it ships an email-CTA intake, so
  the first lead→follow-up loop works immediately).
- **Resend follow-up: ready** to point at the new URL (proof email already verified, dedup-guarded).
- **Facebook one-post approval (`13eafcab`): ready** to link to the new URL once approved +
  `publish_enabled=true` (keep the one-post limit).

---

## Next recommended action (exactly one)
**Confirm the live Netlify URL and that the GitHub deploy is correctly configured**, then share the
URL so the $97 funnel, Resend follow-up, and the Facebook test post can all point to it.

Steps for Ray:
1. Netlify dashboard → this site → confirm **Build command `npm run build`**, **Publish directory
   `dist`**, and the **VITE env vars** above are set; trigger/confirm a deploy from `main`.
2. Open `https://<your-netlify-domain>/goclear-apex-readiness.html` and confirm it loads.
3. Send me the domain and I'll verify the page is live and update this status to "money-ready".

(Do not manual-deploy — the GitHub path is now the source of truth. Manual `netlify deploy` only if
the GitHub deploy fails.)

---

### Appendix
- Files inspected: `reports/runtime/nexus_watch_report_latest.md`,
  `reports/manual_publish/goclear_apex_netlify_deploy_package.md`,
  `docs/operations/NEXUS_LIVE_OPERATIONS.md`, `public/goclear-apex-readiness.html`,
  `dist/goclear-apex-readiness.html`; git-tracked Netlify config search (none found).
- Commands run: `git status/log`, `npm run build` (pass), `npm run nexus:watch` (pass), grep for
  committed URL/netlify config.
- Git: branch `main`, HEAD `a20e885`, working tree clean, **ahead of origin by 1 (the audit commit
  `a20e885` is unpushed)** → Ray should `git push origin main` when ready.
- Safety: no secrets printed/committed, no `.env` read, no deploy, no publish/send/trade, no
  scheduler started.
