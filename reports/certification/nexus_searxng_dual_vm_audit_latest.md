# Nexus Dual Oracle VM SearXNG Compatibility Audit

## CHECKPOINT

- START_SHA: `f0d6789c3f1bd33e3459df64ef533a2b47a2d4ee`
- END_SHA: `f0d6789c3f1bd33e3459df64ef533a2b47a2d4ee`
- BRANCH: `main`
- CHANGES_MADE: `REPORT_ONLY`
- Installation or OCI mutation: `NO`

## VM 1 — nexus-llm-worker

- REACHABLE: `YES`
- ARCH: `aarch64`
- OS: Oracle Linux Server 9.7
- CPU: 4 OCPU / 4 logical CPUs
- RAM: approximately 22 GiB visible
- RAM_AVAILABLE: approximately 21 GiB at audit time
- SWAP: 5 GiB configured, 0 B used
- DISK_FREE: approximately 12 GiB on `/`
- LOAD: 0.02 / 0.02 / 0.00 at audit time
- CURRENT_WORKLOAD: Ollama service active; Gemma installed but unloaded; normal Oracle monitoring/system services
- DOCKER: not installed/detected
- PODMAN: not installed/detected
- OLLAMA: active, loopback-only on `127.0.0.1:11434`, version `0.21.2`
- GEMMA: `gemma3:4b` installed; approximately 3.3 GB model; no active resident model at audit time
- OUTBOUND_NETWORK: DNS and HTTPS probes succeeded
- SEARXNG_COMPATIBILITY: `STRONG`
- RAM_COEXISTENCE: `STRONG` based on approximately 21 GiB available and 0 B swap use; inference-time contention still requires bounded concurrency
- CPU_COEXISTENCE: `ACCEPTABLE_WITH_LIMITS`; Gemma CPU inference can contend with four cores, so SearXNG concurrency should remain low
- DISK_COEXISTENCE: `ACCEPTABLE_WITH_LIMITS`; approximately 12 GiB free, no container images or SearXNG data currently present
- OPERATIONAL_ISOLATION: `GOOD` if SearXNG remains a separate loopback-bound supervised service
- SECURITY_FIT: `GOOD`; private Mac-to-loopback SSH tunnel is compatible; no public SearXNG port required

## VM 2 — OpenChatAI

- REACHABLE: `UNKNOWN`
- CONNECTION: `CONNECTION_INFO_REQUIRED`
- ARCH/CPU/RAM/DISK: `NOT_OBSERVED`
- CURRENT_WORKLOAD: `UNKNOWN`; the VM name must not be treated as proof of emptiness
- DOCKER/PODMAN: `NOT_OBSERVED`
- SEARXNG_COMPATIBILITY: `UNKNOWN`
- OOM_RISK: `UNKNOWN`; the known 1 GB RAM / 1 OCPU shape makes containerized SearXNG marginal even if otherwise empty
- SECURITY_FIT: `POTENTIALLY_GOOD`, but not selectable until workload and private connectivity are proven

Safe sources checked for connection metadata included local SSH configuration/history and Nexus repository/configuration references. No usable OpenChatAI endpoint, username, or key path was found. No guessed connection attempt was made.

## NEXUS

- SEARXNG_PROVIDER_CONTRACT: existing Hermes provider abstraction supports SearXNG
- CREDENTIAL_ID: `credential.searxng.web_search.prod.v1`
- CANONICAL_ALIAS: `NEXUS_SEARXNG_WEB_SEARCH_BASE_URL`
- LEGACY_ALIASES: `SEARXNG_URL`, `ALPHA_SEARXNG_URL`
- EXISTING_ADAPTER: SearXNG HTTP JSON search path exists in `scripts/hermes/hermes_web_search.py`
- FALLBACK_ROUTER: provider priority includes Brave, Tavily, SerpAPI, then SearXNG
- SECURE_TUNNEL_REUSE: existing Oracle Ollama SSH-tunnel convention can be reused later with a separate local port and loopback destination

## COST

- CURRENT_COST_EVIDENCE: `$0.00` for nexus-llm-worker per supplied OCI evidence; OpenChatAI is shown Always Free in supplied console evidence
- NEW_PAID_RESOURCES_REQUIRED: `NO`
- FUTURE_COST_GUARANTEE: `NO`
- OCI changes: `NONE`

## RECOMMENDATION

- PREFERRED_VM: `nexus-llm-worker`
- PREFERRED_DEPLOYMENT: `OPTION A — SearXNG alongside Ollama/Gemma, loopback-bound and reached only through a supervised SSH tunnel`
- WHY: It is the only VM directly audited, has substantial measured RAM headroom, unused swap, low load, sufficient disk for a minimal deployment, proven outbound HTTPS, and an existing private tunnel pattern.
- SECOND_CHOICE: OpenChatAI only after Ray supplies/proves connection details and a read-only workload audit confirms sufficient headroom. Its 1 GB / 1 OCPU shape is marginal for containerized deployment.
- REJECTED_OPTION: `OPTION B` is not supported by evidence because OpenChatAI is unreachable and un-audited.
- INSTALLATION_READY: `NO — audit complete; installation requires a separate approved change`

## FINAL DECISION

`A = SearXNG on nexus-llm-worker with Gemma`, subject to a later bounded installation plan and explicit low-concurrency/private-bind configuration.

## BLOCKERS

- OpenChatAI connection information is unavailable: `OPENCHATAI_CONNECTION=CONNECTION_INFO_REQUIRED`.
- No measured OpenChatAI workload/resource evidence exists.
- This audit did not verify OCI billing through an automated cost API; supplied OCI cost evidence remains separate from technical compatibility.
