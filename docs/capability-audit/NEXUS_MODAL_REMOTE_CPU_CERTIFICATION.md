# Modal Remote CPU Certification (Phase I-C)

Status: certified live on 2026-08-21.

## Deployment

- Provider: Modal, workspace profile `goclearonline`
- Plan basis: Starter/free entitlement; billing showed `billed_cost=0` and
  `metered_cost` fully covered by credits during certification
- CPU only; no GPU
- Minimum containers: 0
- Maximum containers: 1
- Scale-to-zero: observed (`tasks=0` after the idle window)
- No scheduler, autonomous retry loop, or always-on worker was added
- OCI remains deferred

The deployed app uses the existing Linux worker image and evidence-ingestion
dependencies. Modal's native authenticated SDK invocation is the Nexus
transport path. The existing Nexus HMAC is verified by the worker for every
job. The web compatibility endpoints remain Modal proxy-authenticated and are
not used as an unauthenticated fallback.

## Authority

The worker allowlist is bounded to `evidence_ingestion.crawl4ai` for live
remote execution. It has no shell, approval, work-order, publishing, Stripe,
trading, messaging, or Mission Control mutation authority. Remote output is
validated and then persisted by Nexus through the canonical evidence artifact,
receipt, and intake handoff functions.

## Live evidence

The benign public URL `https://example.com/` completed with Crawl4AI,
Playwright, and headless Chromium. Nexus accepted the provider-neutral result,
preserved provenance/source/material hashes, and wrote canonical local
evidence/receipt artifacts. Repeating the source produced the same material
hash and `DUPLICATE` on Nexus acceptance. Live prohibited URL classes were
rejected as bounded `PRIVATE_NETWORK_BLOCKED` or `INVALID_URL` results.

Modal startup logs also exposed and fixed a deployment-only `/root/modal_app.py`
path assumption; the wrapper now uses `/app` inside the image while retaining
the repository path only for local image construction.

## Cost and lifecycle

Certification billing showed `$0` billed cost; metered usage was covered by
included credit. The app is deployed with zero idle tasks and is not a Nexus
scheduler. Future lifecycle management may choose on-demand execution, but
Nexus remains the sole authority deciding whether a governed job exists.
