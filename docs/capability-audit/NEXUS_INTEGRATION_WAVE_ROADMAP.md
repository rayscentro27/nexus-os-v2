# Nexus Integration Wave Roadmap

## Current state

- Autonomy foundation: **COMPLETE**.
- Mission Control: **COMPLETE**.
- Capability Advantage Audit: **COMPLETE after this documentation commit**.

## Recommended waves

### Wave A — Research and knowledge advantage

Pilot MarkItDown plus a contained Crawl4AI adapter; add Lighthouse evidence;
consolidate provenance and freshness into existing research adapters. Alpha
remains advisory and separately gated.

### Wave B — Business intelligence

Extend opportunity, revenue, SEO, and GoClear reporting using the canonical
research/result/approval path. Do not add new publishing authority.

### Wave C — Remote worker foundation

Implement the provider-neutral job envelope, worker router, signed result,
receipt, timeout, cost, tenant, and failure-isolation contracts. Start with one
remote CPU worker; defer GPU provisioning.

### Wave D — Creative Studio

Pilot ComfyUI only after licensing/model review; use Remotion for template-based
composition; render in isolated workers; retain approval before distribution.

### Wave E — Human interface

Pilot whisper.cpp for private STT, then evaluate consented TTS and async avatar
rendering. Streaming voice and meeting presence require a separate media-plane
architecture.

### Wave F — Business platform

Extract business configuration from GoClear: identity, brand, offers,
departments, knowledge, policies, approvals, integrations, and reporting. Use a
second business as the validation case before claiming multi-tenant readiness.

### Wave G — TradingOps

Build research/data contracts first; compare VectorBT, NautilusTrader, LEAN,
and options-specific tooling. Progress research → backtest → robustness →
walk-forward → Monte Carlo → paper/demo → review. No funded trading.

## First pilot

- **Capability:** canonical document and public-web evidence ingestion.
- **Projects:** MarkItDown first; Crawl4AI contained comparison.
- **Disposition:** PILOT.
- **Location:** Mac Mini isolated worker for local documents; remote CPU for
  public crawl.
- **Acceptance:** deterministic source hashes, provenance, bounded timeout,
  redaction, no PII egress, retry/failure receipts, Mission Control visibility,
  and zero impact to certified services.

## Second pilot

- **Capability:** provider-neutral remote CPU worker.
- **Project:** no external platform required initially; fixture worker behind a
  Nexus adapter, then Coolify or a simple container host evaluation.
- **Disposition:** PILOT.
- **Location:** REMOTE_CPU_WORKER.
- **Acceptance:** signed job/result, scoped credentials, timeout, idempotency,
  cost record, provider failure isolation, and no authority outside Nexus.

## Third pilot

- **Capability:** private speech-to-text.
- **Project:** whisper.cpp.
- **Disposition:** PILOT.
- **Location:** MAC_MINI_ISOLATED_WORKER.
- **Acceptance:** consented fixture audio, local-only mode, transcript hash,
  deletion policy, bounded latency, no raw audio in long-term logs, and Hermes
  context integration only through a governed adapter.
