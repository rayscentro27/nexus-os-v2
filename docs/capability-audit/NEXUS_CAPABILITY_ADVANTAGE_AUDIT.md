# Nexus Capability Advantage Audit

**Phase:** Post-Mission-Control / pre-integration certification
**Date:** 2026-08-21
**Disposition:** research and architecture only; no third-party installation

## Executive decision

Nexus already has the control plane that most agent products would have to
build: a certified continuous loop, Active Operator, Recovery Check, Hermes,
governed work orders and approvals, Mission Control, receipts, launchd
evidence, and explicit financial/shell boundaries. The advantage is therefore
not replacing Nexus with a fashionable framework. It is attaching carefully
bounded capability workers to Nexus adapters.

The recommended first pilot is **document and web evidence ingestion** using
MarkItDown plus a contained Crawl4AI evaluation, with Nexus retaining source
identity, provenance, redaction, approval, receipt, and Mission Control truth.
No package is installed by this audit.

## Baseline evidence

- Git HEAD at audit start: `00e24ddd08ec1a0b5ad40892a8badc46e27f7868`.
- Branch: `main`.
- Continuous Loop, Active Operator, Recovery Check, and Hermes LaunchAgents
  were present with exit code `0`.
- Mission Control snapshot: `HEALTHY`; pending approvals `0`; open work `0`.
- Stripe autonomous authority: `DISABLED`.
- Arbitrary shell: `UNAVAILABLE`.
- Funded live trading: `DISABLED`.
- Natural three-hour Recovery Check dispatch: `NOT_YET_OBSERVED` at the audit
  window; the next scheduled check was still later than the observation time.

## Current capability inventory

| Family | State | Existing evidence / decision |
|---|---|---|
| Agent orchestration | STRONG | Hermes routers, model router, specialist routing, bounded runners. Keep Nexus contract primary. |
| Autonomous loops | STRONG | Certified continuous loop with ledger, hashes, NO_CHANGE, launchd recovery. |
| Active operations | STRONG | Active Operator runner, bounded work, receipts, heartbeat. |
| Recovery / self-healing | STRONG | Recovery Check with authority classification, escalation, receipt, heartbeat. |
| Governance | STRONG | Action policy, capability access, approvals, work orders, receipts. |
| Approvals | STRONG | Governed approval store and Ray Review paths. |
| Work orders | STRONG | Canonical governed work-order primitives and idempotency. |
| Mission Control | STRONG | Read-only canonical aggregation and admin surface. |
| Hermes | STRONG | Telegram operator, status routing, state grounding, safety blocks. |
| Alpha | PARTIAL | Research/advisory foundations exist but activation is intentionally deferred. |
| Memory | PARTIAL | Hermes decision memory, local stores, Nova historical artifacts; consolidation is needed. |
| Knowledge / retrieval | PARTIAL | Approved knowledge, report/search adapters, research memory; graph/corpus layer is not canonical. |
| Supabase / durable state | ADEQUATE | Existing adapters, RLS/readiness audits, governed stores; multi-tenant product boundary remains future work. |
| Research intake | STRONG | Source scouts, URL/search/research pipelines, approval-aware research artifacts. |
| YouTube / transcripts | ADEQUATE | Metadata, transcript intake, capture queue, normalization and review scripts. |
| URL/web ingestion | PARTIAL | Existing web-search and source capture; robust browser/crawl worker is a gap. |
| Crawling | SCAFFOLD | Existing research scripts, no isolated canonical crawl service. |
| Web research | ADEQUATE | Hermes research adapters and evidence-oriented reports; freshness/scale can improve. |
| Browser automation | PARTIAL | Playwright/browser smoke infrastructure exists; governed authenticated research worker is not a product capability. |
| Computer use | MISSING | No approved autonomous computer-use authority; do not add in core. |
| Document ingestion/conversion | PARTIAL | HTML preview/conversion and intake exist; format breadth/provenance adapter is a gap. |
| CRM / client operations | ADEQUATE | Client portal, client workflow, vault and support concepts exist; external CRM is not the brain. |
| Opportunity detection | ADEQUATE | Opportunity lab, Alpha scoring, money/revenue pipelines exist. |
| Revenue intelligence | ADEQUATE | Revenue streams, offers, approval lanes, and GoClear reporting exist. |
| Affiliate intelligence | ADEQUATE | Affiliate opportunity tracker and approval-aware research exist. |
| SEO | ADEQUATE | Keyword types, SEO scouts and marketing feeders exist; technical crawl evidence can improve. |
| Marketing | ADEQUATE | Drafts, campaigns, content tests and approval lanes exist. |
| Email / newsletters | PARTIAL | Draft and approval lanes exist; no autonomous sending authority. |
| Social distribution | PARTIAL | Publishing adapters and approvals exist; activation is intentionally blocked. |
| Creative generation | PARTIAL | Creative Studio feeder, briefs and approvals exist; generation workers are not activated. |
| Image generation | SCAFFOLD | Asset/brief abstractions exist; no governed image worker. |
| Video generation | MISSING | No safe, isolated generation worker; GPU placement is future research. |
| Video editing/composition | PARTIAL | Video research/rating and content pipelines exist; programmatic render adapter is not canonical. |
| Speech-to-text | SCAFFOLD | Voice-ready renderer and research references; no activated STT worker. |
| Text-to-speech | SCAFFOLD | Voice-ready output concepts; no activated TTS authority. |
| Voice cloning | MISSING | Requires explicit consent, identity, and licensing controls. |
| Streaming voice | MISSING | Architecture is not activated. |
| Real-time voice conversation | SCAFFOLD | Hermes conversational routing exists; low-latency audio loop does not. |
| Avatar / presenter | SCAFFOLD | Assets and UI concepts exist; no renderer or provider adapter. |
| Real-time avatar | MISSING | Requires streaming media architecture. |
| Meeting presence | MISSING | Research only; no meeting bot or WebRTC authority. |
| Remote workers | PARTIAL | Shell wrappers, process registry and bounded runners exist; no normalized remote job plane. |
| GPU workers | MISSING | No provisioned GPU worker; intentionally so. |
| Deployment / orchestration | ADEQUATE | launchd is strong for local control plane; remote deployment abstraction is absent. |
| Secrets / security | STRONG | Runtime environment isolation, redaction, RLS, approval gates, no arbitrary shell. |
| Observability | ADEQUATE | Heartbeats, receipts, Mission Control, scheduler evidence; fleet metrics remain future. |
| Model routing | ADEQUATE | `scripts/model_router.py`, Hermes provider abstractions and bounded status. |
| Trading research | PARTIAL | Trading Lab, Alpha research, Oanda demo and reports; unified research engine is absent. |
| Backtesting | PARTIAL | Backtest import/dry-run adapters and reports; multi-asset/options-grade engine is absent. |
| Paper / demo trading | ADEQUATE | Oanda practice/demo paths exist with explicit safety. |
| Forex | ADEQUATE | Oanda practice connector and read-only checks; no funded execution. |
| Options | MISSING | No validated historical chain/assignment/multi-leg engine. |
| Crypto | SCAFFOLD | Research references; no approved paper venue/data contract. |
| Equities / ETFs | SCAFFOLD | Research references; no canonical paper adapter. |
| Futures | MISSING | Defer until data/risk prerequisites exist. |
| Risk management | PARTIAL | Trading policies and review cards exist; portfolio Greeks/options risk is missing. |
| Portfolio analytics | SCAFFOLD | Reports and trading briefs exist; canonical portfolio/risk store is missing. |
| Trading journal | PARTIAL | Reports/receipts exist; a normalized journal is future work. |
| Multi-business configuration | SCAFFOLD | Product vision and GoClear-specific configuration exist; reusable template contract is not implemented. |
| SaaS / multi-tenancy | PARTIAL | Supabase/RLS/client boundaries exist; tenant-aware worker plane is not ready. |
| Business templates | SCAFFOLD | GoClear is the proving ground; template schema and lifecycle are future. |

## Legacy asset disposition

**REUSE:** continuous-loop, Active Operator, Recovery Check, Hermes, Mission
Control, approvals, work orders, receipts, RLS, Oanda practice safety, source
capture, YouTube/transcript intake, model-router and launchd wrappers.

**WRAP:** Alpha research, trading research, browser smoke tooling, creative
feeders, Supabase adapters, client workflows, email/social approval lanes.

**ADAPT:** existing Hermes memory/report indexes, research-to-content pipelines,
Oanda demo reports, and video research artifacts.

**REFERENCE_ONLY:** legacy Nova Telegram and old v1 schedulers, stale Mission
Control producers, historical provider experiments, and generated runtime
noise.

**DECOMMISSION / IGNORE:** duplicate Telegram pollers, v1 recovery daemons,
unbounded shell bridges, and any artifact that would become a second health,
approval, work-order, scheduler, or trading authority.

## Top five capability advantages

1. **Evidence-first web/document ingestion** — MarkItDown plus a Crawl4AI
   pilot behind the existing source/provenance adapters. Low architectural
   risk; reusable across businesses.
2. **Governed remote worker contract** — design-only worker adapter and receipt
   schema before provisioning compute. This unlocks CPU/GPU without moving
   authority out of Nexus.
3. **Programmatic branded video composition** — evaluate Remotion as a bounded
   renderer, not as an editor or operator. Useful for repeatable templates.
4. **Private/local transcription** — evaluate whisper.cpp as an isolated,
   optional local worker for privacy-sensitive audio.
5. **Trading research engine evaluation** — contained paper/research comparison
   of NautilusTrader plus existing Oanda/demo adapters; no broker credentials or
   live execution.

## Anti-bloat decision

Nexus must not add a second scheduler, work-order store, approval store,
Mission Control, health authority, memory truth source, CRM brain, recovery
engine, operator command model, secret store, or trading execution authority.
External projects are workers, libraries, or views behind adapters. The
canonical path remains:

`NEXUS → governed job → capability adapter → structured result → validation → receipt → Mission Control`.

## Primary source register

- [LangGraph](https://github.com/langchain-ai/langgraph) — MIT, stateful graph
  orchestration; useful for contained workflows, not a Nexus replacement.
- [Firecrawl](https://github.com/firecrawl/firecrawl) — AGPL-3.0, self-host/API
  web extraction; commercial distribution needs license review.
- [Crawl4AI self-hosting](https://docs.crawl4ai.com/core/self-hosting/) —
  authenticated, loopback-by-default Docker server and artifact-oriented API.
- [Microsoft MarkItDown](https://github.com/microsoft/markitdown) — MIT
  document-to-Markdown conversion.
- [ComfyUI](https://github.com/comfy-org/ComfyUI) — GPL-3.0, modular visual
  generation engine.
- [Remotion](https://github.com/remotion-dev/remotion) — active React video
  composition; commercial licensing must be reviewed before product use.
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) — local Apple Silicon-
  friendly speech recognition implementation.
- [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) — LGPL-3.0,
  Rust-native multi-asset trading engine with research/live parity claims.
- [n8n license](https://docs.n8n.io/privacy-and-security/sustainable-use-license/)
  — fair-code restrictions make product embedding a legal review item.
- [Coolify](https://coolify.io/docs/get-started/introduction) — self-hosted PaaS;
  infrastructure convenience, not Nexus authority.
- [RunPod pricing](https://www.runpod.io/pricing) and [Modal pricing](https://modal.com/pricing)
  — burst GPU/provider references; prices are usage-dependent and must be
  rechecked at pilot time.
