# Nexus Open-Source Decision Matrix

Scores are directional 0–5 ratings, weighted toward capability advantage,
governance compatibility, commercial fit, replacement ease, and operational
burden. Popularity is only a weak signal. No candidate was installed.

| Candidate | Primary disposition | Weighted score | Fit | Location | Key decision |
|---|---:|---:|---|---|---|
| MarkItDown | PILOT | 4.3 | Document conversion adapter | Mac Mini isolated worker / CPU | MIT, small, deterministic, provenance-friendly |
| Crawl4AI | PILOT | 4.1 | Governed crawl/extract worker | Remote CPU or isolated local | Self-hostable, browser-backed, auth defaults; validate resource use |
| Firecrawl | WATCH | 3.8 | Managed/self-host crawl service | Managed API or remote CPU | Strong extraction, but AGPL and hosted economics require review |
| LangGraph | ADAPT | 3.5 | Selected workflow patterns | Remote CPU if used | Durable graph/checkpoint patterns; overlaps certified orchestration |
| Lighthouse | EXTEND | 4.0 | SEO/performance evidence | Remote CPU | Narrow diagnostic role, no authority |
| GraphRAG patterns | ADAPT | 3.6 | Retrieval/graph patterns | Remote CPU/cloud DB | Do not create second truth source |
| Twenty CRM | WATCH | 3.0 | External CRM adapter | Self-hosted cloud | Potential tenant CRM, but Nexus already owns client/workflow brain |
| Chatwoot | WATCH | 3.2 | Support inbox adapter | Self-hosted cloud | Useful channel surface, not customer authority |
| n8n | REJECT for core / WATCH internal | 2.6 | Generic automation | Remote CPU | Fair-code/product-hosting restrictions and duplicate orchestration risk |
| Mautic | WATCH | 3.0 | Campaign system | Self-hosted cloud | Only if campaign volume justifies external campaign state |
| Listmonk | PILOT later | 3.7 | Newsletter delivery | Remote CPU/cloud | Narrow delivery worker behind approvals; no autonomous sending |
| Postiz | WATCH | 2.9 | Social scheduling | Self-hosted cloud | Publishing authority and product fit not ready |
| Uptime Kuma | ADAPT | 3.4 | Endpoint monitoring | Remote CPU | Supplementary probes only; Mission Control remains health authority |
| Infisical | WATCH | 3.5 | Secret management | Self-hosted cloud | Evaluate before multi-tenant scale; do not add second store now |
| Coolify | WATCH | 3.4 | Deployment convenience | Remote CPU | Useful remote worker PaaS, not control plane |
| Open WebUI | REJECT for core | 2.5 | Model UI | Isolated optional service | Duplicates Hermes/Mission Control UX |
| ComfyUI | PILOT later | 4.0 | Image workflow engine | Remote GPU | Strong workflow API; GPL and model licenses require review |
| Remotion | PILOT later | 4.2 | Programmatic video | Remote CPU/GPU render worker | Strong template fit; commercial license review |
| OpenCut variants | WATCH | 2.7 | Interactive editor | Local UI | Multiple unrelated projects; maturity/identity uncertainty |
| whisper.cpp | PILOT later | 4.1 | Private STT | Mac Mini isolated worker | Apple Silicon, offline, low privacy exposure |
| Coqui TTS | WATCH | 2.8 | Local TTS | Remote GPU/local | Repository activity/licensing/model rights need revalidation |
| SadTalker-style avatar | WATCH | 2.6 | Async avatar | Remote GPU | Pre-rendered only; identity/consent and model license risks |
| NautilusTrader | PILOT later | 4.2 | Multi-asset research engine | Remote CPU | Strong options/venue abstractions; LGPL and live-risk boundary |
| LEAN | WATCH | 3.8 | Broad backtesting | Remote CPU | Strong asset coverage; data/licensing and cloud coupling review |
| VectorBT | ADAPT | 3.7 | Vectorized research | Mac Mini/remote CPU | Excellent exploratory math; not an execution authority |
| Freqtrade | REJECT for core | 2.8 | Crypto bot | Isolated remote worker | Operational bot assumptions conflict with no funded trading |
| Backtrader | REFERENCE_ONLY | 2.4 | Legacy backtesting | Mac Mini | GPL and older architecture; useful conceptual reference |
| Options Portfolio Backtester | PILOT research-only | 3.8 | Options portfolio research | Remote CPU | Promising chain/Greeks model; verify data/license before adoption |

## Maintenance / license evidence snapshot

This is a point-in-time research snapshot, not a promise that versions or
licenses will remain unchanged. Recheck before any pilot:

| Candidate | Evidence observed | Commercial implication |
|---|---|---|
| LangGraph | Active GitHub releases; current package metadata reports 1.2.x and MIT | Compatible for an isolated library use; still overlaps orchestration |
| Firecrawl | Repository states AGPL-3.0 and documents self-host/cloud split | Legal review before embedding or offering a hosted product |
| Crawl4AI | 0.9 self-host docs describe auth-by-default, loopback binding, strict request boundaries | Good security posture if isolated; test resource use and browser escape surface |
| MarkItDown | Microsoft repository LICENSE is MIT | Low-friction adapter candidate; audit transitive notices |
| ComfyUI | Repository reports GPL-3.0 and active releases | Model licenses and GPL product distribution require counsel review |
| Remotion | Repository reports active releases and warns some commercial use requires a company license | Budget license review before commercial render service |
| whisper.cpp | Official project documents Apple Silicon/Metal and CPU-only support | Strong private local candidate; model files still need license review |
| NautilusTrader | Repository documents LGPL-3.0, release provenance, macOS/Linux support, and options | Keep as isolated research/paper engine; never infer live authorization |
| Backtrader | Repository reports GPL-3.0 and an older Python architecture | Reference only; not a new platform dependency |
| n8n | Official docs call the Sustainable Use License fair-code and restrict product/hosted use cases | Do not embed as Nexus SaaS core without commercial agreement |
| Coolify | Official docs describe self-hosted PaaS; pricing shows free self-hosted and paid managed control plane | Useful deployment helper, not worker authority |

The links in [the capability audit](NEXUS_CAPABILITY_ADVANTAGE_AUDIT.md) point
to the primary repository or official documentation used for this snapshot.

## Disposition rules

- **REUSE:** only where the project is a narrow capability and the license,
  security, and operational model are acceptable.
- **EXTEND:** Nexus remains primary; external code adds diagnostics or a
  bounded adapter.
- **ADAPT:** borrow patterns without importing the whole platform.
- **PILOT:** isolated proof with fixtures, receipts, no production authority.
- **WATCH:** meaningful but prerequisites, legal review, or maturity are not
  ready.
- **REJECT:** duplicate, unsafe, commercially incompatible, stale, or
  architecturally wrong.

## Governance adapter contract

Every adopted candidate must accept a Nexus job containing `job_id`, tenant,
capability, sensitivity, bounded input references, timeout, and approval state.
It returns a versioned structured result with status, source references,
content hashes, cost/usage metadata, redaction status, and failure details.
The adapter enforces timeout, retry budget, network policy, PII boundary, and
credential scope. Only Nexus can create consequential work, approve, publish,
move money, or write canonical health state.
