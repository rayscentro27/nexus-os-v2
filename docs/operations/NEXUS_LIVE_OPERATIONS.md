# Nexus Live Operations

Status: live-output checks enabled, scheduler disabled by default.

## Manual Run

From the repo root:

```bash
npm run nexus:watch
```

This runs one bounded activation pass. It checks GoClear/Apex landing page readiness, Netlify config, Resend email readiness, social publish gates, Oanda demo/paper status, Oracle worker reachability, and Hermes report explanation.

## Netlify (GitHub-connected deploy)

The deploy path is **push `main` → Netlify builds and deploys**. Build settings are self-documented
in `netlify.toml` (command `npm run build`, publish dir `dist`, SPA fallback redirect).

GitHub-connected deploy does **not** require local Netlify CLI tokens:

- `NETLIFY_AUTH_TOKEN` / `NETLIFY_SITE_ID` are only for optional Netlify **CLI/API verification**.
  The watch loop reports their presence as `cli_capable`, not as a deploy blocker.
- To let Nexus track the live site, set the **public URL** (safe, not a secret):
  `NEXUS_NETLIFY_PUBLIC_URL` (or browser-exposed `VITE_GOCLEAR_PUBLIC_URL`).

The watch loop classifies Netlify as:

- `deploy_mode=github_connected_public_url` when a public URL is set (status
  `public_url_configured_needs_live_verification`).
- `deploy_mode=github_connected_assumed` when `netlify.toml` is present but no URL is set yet
  (blocker `missing_public_url_in_repo_or_env`).

Nexus does not claim the landing page is live until a public URL is provided (and ideally verified).
Once the URL is known, point Resend follow-up and the Facebook test post at
`<public-url>/goclear-apex-readiness.html`. Also set `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`,
and `VITE_HERMES_CHAT_ENABLED=true` in the Netlify UI so the app build has its Supabase/Hermes config.

## Scheduler

No scheduler is installed or started by default.

To enable later, use one scheduler on one host only, and point it at:

```bash
cd ~/nexus-os-v2 && npm run nexus:watch
```

Recommended cadence while the $97 review offer is being tested:

- Every business morning.
- Once mid-afternoon.
- No more than hourly unless stronger cross-host deduplication is added.

## Lock And Overlap Protection

The runner uses a nonblocking file lock:

```text
reports/runtime/nexus_watch.lock
```

If another run is active, a second run exits with `blocked_overlap`.

## Reports And Logs

Latest report:

```text
reports/runtime/nexus_watch_report_latest.md
reports/runtime/nexus_watch_report_latest.json
```

Runtime reports are ignored by git. Reusable manual packages are committed under:

```text
reports/manual_publish/
```

## Hermes

Hermes receives a safe Watch Report summary only. The report must not include secrets, customer private data, SSNs, credit reports, bank docs, tax docs, passwords, reset tokens, service-role keys, or raw customer files.

Hermes should explain:

- What ran.
- What changed.
- What is live.
- What is blocked.
- What Ray should do next.
- Whether the loop is healthy.
- What can run again.

## Failure-To-Task Pattern

Each blocked channel should become a concrete next task:

- Netlify missing: add `NETLIFY_AUTH_TOKEN` and `NETLIFY_SITE_ID`, or manually deploy `dist`.
- Resend missing: add `RESEND_FROM_EMAIL`; `RESEND_TO_EMAIL` defaults to Ray when absent.
- Social blocked: confirm token, account row, and `publish_enabled`; keep one-post limit.
- Oanda blocked: require demo/practice flags; no funded/live trading.
- Oracle blocked: confirm host, user, key path, and SSH reachability; do not restart production workers from the watch loop.

## Safety

The loop must not start paid ads, mass email, spam, live/funded trades, destructive schema changes, firewall weakening, or unbounded background work.
