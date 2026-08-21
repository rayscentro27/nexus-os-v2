# Nexus Compute Placement Matrix

## Placement rule

**Nexus authority stays in Nexus.** A remote worker supplies computation only.
It cannot approve, publish, send customer communications, move money, change
governance, or become a health authority.

| Capability | Candidate | Mac Mini | CPU cloud | GPU cloud | Managed API | Hybrid | Recommended location | Privacy |
|---|---|---:|---:|---:|---:|---:|---|---|
| Status/governance | Nexus native | EXCELLENT | POOR | N/A | POOR | GOOD | MAC_MINI_LOCAL | LOCAL_REQUIRED |
| Document conversion | MarkItDown | EXCELLENT | GOOD | N/A | POSSIBLE | GOOD | MAC_MINI_ISOLATED_WORKER | LOCAL_PREFERRED |
| Web crawl/extract | Crawl4AI | POSSIBLE | EXCELLENT | N/A | GOOD | EXCELLENT | HYBRID | CLOUD_ACCEPTABLE for public data |
| Web search/extraction | Firecrawl | POOR | POSSIBLE | N/A | EXCELLENT | GOOD | MANAGED_API or REMOTE_CPU_WORKER | CLOUD_ACCEPTABLE |
| SEO diagnostics | Lighthouse | GOOD | EXCELLENT | N/A | N/A | GOOD | REMOTE_CPU_WORKER | CLOUD_ACCEPTABLE |
| Embeddings/retrieval | Existing adapters | GOOD | GOOD | POSSIBLE | GOOD | EXCELLENT | HYBRID | depends on corpus |
| Image generation | ComfyUI | POOR | POOR | EXCELLENT | GOOD | EXCELLENT | REMOTE_GPU_WORKER | CLOUD_ACCEPTABLE |
| Video composition | Remotion | POSSIBLE | EXCELLENT | POSSIBLE | N/A | EXCELLENT | REMOTE_CPU_WORKER / HYBRID | asset-dependent |
| Video generation | model-specific | POOR | POOR | EXCELLENT | GOOD | EXCELLENT | REMOTE_GPU_WORKER | CLOUD_ACCEPTABLE |
| STT | whisper.cpp | EXCELLENT | GOOD | POSSIBLE | GOOD | GOOD | MAC_MINI_ISOLATED_WORKER | LOCAL_REQUIRED for sensitive audio |
| TTS | provider/model adapter | POSSIBLE | GOOD | GOOD | EXCELLENT | EXCELLENT | HYBRID | consent-sensitive |
| Avatar rendering | model-specific | POOR | POOR | EXCELLENT | GOOD | EXCELLENT | REMOTE_GPU_WORKER | consent/asset-specific |
| Trading research | VectorBT/Nautilus | GOOD | EXCELLENT | POSSIBLE | N/A | EXCELLENT | REMOTE_CPU_WORKER | market data policy |
| Options analytics | Nautilus/supplement | POSSIBLE | EXCELLENT | POSSIBLE | POSSIBLE | EXCELLENT | REMOTE_CPU_WORKER | financial data restricted |

## Cost behavior

- Local control-plane workloads: **NEGLIGIBLE incremental cost / FIXED**.
- CPU workers: **LOW to MEDIUM / USAGE_BASED or BURST**; serverless fits short
  deterministic transforms, persistent workers fit browser jobs.
- GPU workers: **HIGH to VERY_HIGH / BURST**; on-demand is preferred until
  measured utilization justifies persistence. RunPod documents Pods,
  Serverless, and Clusters as separate billing/deployment models; Modal also
  exposes GPU-oriented usage pricing. Recheck prices at pilot time.
- Managed APIs: **LOW implementation burden / USAGE_BASED**, but data retention,
  rate limits, lock-in, and commercial terms must be explicit.

## Failure isolation

Never run crawlers, browsers, ComfyUI, video generation, avatar rendering,
large TTS/STT models, or Trading Lab simulations inside the core Nexus
process. Use a subprocess for small local jobs and containers/remote workers
for heavy, networked, or untrusted workloads. Each job must time out, return a
failure receipt, and leave the certified control plane healthy.

## Offline behavior

- Core governance/status/approvals: **CORE_OFFLINE_CAPABLE**.
- Local MarkItDown and whisper.cpp: **DEGRADED_OFFLINE** or
  **CORE_OFFLINE_CAPABLE** for local inputs.
- Public web crawl, managed APIs, remote CPU/GPU: **OPTIONAL_CLOUD_DEPENDENT**.
- Trading research with cached data: **DEGRADED_OFFLINE**; live market data and
  any broker path remain disabled.
