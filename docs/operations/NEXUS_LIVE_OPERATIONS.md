# Nexus Live Operations

Status: live-output checks enabled, scheduler disabled by default.

## Manual Run

From the repo root:

```bash
npm run nexus:watch
```

This runs one bounded activation pass. It checks GoClear/Apex landing page readiness, Netlify config, Resend email readiness, social publish gates, Oanda demo/paper status, Oracle worker reachability, and Hermes report explanation.

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
