# Nexus Oracle Reasoning Resource Fit

Campaign: `HG-WP6.5-HERMES-INTELLIGENCE-STACK-RECONCILIATION-20260830-01`  
Read-only measurements; no packages or services installed.

## Observed baseline

| Metric | Observed |
|---|---|
| Architecture | aarch64 |
| CPUs | 4 |
| RAM | 22 GiB total; about 20 GiB available at capture |
| Swap | about 5 GiB available |
| Root disk | 30 GiB total; about 7.4 GiB free; 75% used |
| Load | approximately 0.00 at capture |
| Uptime | approximately 62 days |
| Services | Hermes 0.20.6 user service, Ollama, SearXNG, Podman-managed components |
| Installed Ollama models | `gemma3:4b`; existing cloud-model entry `deepseek-v4-pro:cloud` |

The root disk, not CPU or RAM, is the near-term constraint. A second stateful multi-container observability or crawling stack would reduce operational margin.

## Placement decisions

| Candidate | Fit | Reason |
|---|---|---|
| LangGraph orchestration | HYBRID_FIT | lightweight graph layer; keep authority/state on Mac and use Oracle Hermes for reasoning |
| GPT Researcher | ORACLE_FIT, bounded pilot | multi-source work can use Oracle/SearXNG, but provider/retriever configuration and output validation are additional complexity |
| Crawl4AI | ORACLE_FIT, wrapped | browser/Chromium belongs on Oracle or an isolated worker; do not add it to the 8 GiB Mac by default |
| Langfuse self-host | NOT_RECOMMENDED currently | official self-host architecture adds Postgres, ClickHouse, Redis/Valkey, and object storage; disk margin is poor |
| DSPy | MAC_FIT for offline evaluation only | low runtime footprint but requires a stable evaluation set and model budget; not a live dependency |
| Playwright/browser automation | ORACLE_FIT, bounded | existing Mac Playwright path exists, but prior Chromium limitations and Mac memory argue for isolated Oracle use |
| Stagehand/Browser Use | ORACLE_FIT or CLOUD_PREFERRED | browser-agent control adds model calls and browser risk; no need before the existing bounded browser path is exhausted |
| Additional local model | NOT_RECOMMENDED without measured need | current `gemma3:4b` is installed; disk and RAM should not be consumed by speculative downloads |

## Resource policy

Mac should retain TruthKernel, credentials, sensitive deterministic processing, lightweight orchestration, and receipts. Oracle should retain Hermes, Ollama, SearXNG, containers, long-running workers, and bounded public research extraction. A hybrid path is required for reasoning: Mac supplies verified evidence and authority; Oracle supplies model execution.

The existing cloud-model entry is inventory evidence only. No cost or permission is inferred from its presence, and it is not recommended as a new route in this audit.

