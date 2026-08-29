# WP4 Phase 0 Repository / Capability / Resource Reconciliation

Date: 2026-08-29
Campaign: `HG-WP4-NEXUS-LOOPS-SKILLS-20260829-01`
Authority: approved TruthKernel campaign gate

Phase 0 completed before new WP4 capability implementation. Discovery was
read-only; secrets and private host identifiers are excluded.

## Mac repositories

| Repository | Path | Remote / revision | Evidence-based purpose | Disposition |
|---|---|---|---|---|
| nexus-os-v2 | `/Users/raymonddavis/nexus-os-v2` | `rayscentro27/nexus-os-v2`, `dce1725` at discovery | Nexus control plane, TruthKernel, Python executors, reports | KEEP_IN_PLACE |
| nexuslive | `/Users/raymonddavis/nexuslive` | `rayscentro27/nexuslive`, `4fb57df` | Earlier Nexus/Hermes Python and operational implementation | WRAP; preserve as reference/legacy |
| nexus-ai | `/Users/raymonddavis/nexus-ai` | `rayscentro27/nexuslive`, `ec879d2` | Older Hermes command-router and strategy code | MIMIC_PATTERN; do not run as competing scheduler |
| nexus-ai-worker | local clone | repository identity not established in bounded audit | Older worker/router variant | ARCHIVE_PENDING; do not activate |
| nexus-hermes-runtime | `/Users/raymonddavis/nexus-hermes-runtime` | `NousResearch/hermes-agent`, `3c27eb623` | Hermes source/runtime reference | KEEP_IN_PLACE; upstream reference, not Nexus-owned |
| nexus-oracle-api | local directory | remote not exposed by bounded inspection | Oracle API integration candidate | WRAP only after interface audit |
| nexus-mobile | `/Users/raymonddavis/nexus-mobile` | `rayscentro27/nexus-mobile`, `127df9f` | Mobile client/UI | KEEP_IN_PLACE; no authority or runtime duplication |
| nexus-os-v2-hermes-cert / wave4 archives | local snapshots | historical snapshots | Prior certification evidence | ARCHIVE |

The Mac working tree contains pre-existing unrelated modifications. They were
not staged or changed by Phase 0. LaunchAgent references were treated as
configuration references, not proof of execution.

## Oracle services

Read-only SSH inventory confirmed Oracle Linux Server 9.7, aarch64, 4-vCPU
Free Tier host with 22 GiB RAM and approximately 20 GiB available memory at
inspection. Active services are `nexus-hermes-0206.service` (user service),
`nexus-searxng.service`, and `ollama.service`; Podman manages the pinned Hermes
container. Existing bind addresses and ports remain private/controlled by the
previous architecture. No service was restarted or reconfigured.

| Service | Status / persistence | Purpose | Placement / overlap |
|---|---|---|---|
| Hermes 0.20.6 | active, user-level supervised | reasoning, sessions, skills, scoped workers | ORACLE_FREE_TIER; WRAP_WITH_NEXUS |
| Ollama / gemma3:4b | active, existing | private local reasoning | ORACLE_FREE_TIER; KEEP_IN_PLACE |
| SearXNG | active, existing | private search/research | ORACLE_FREE_TIER; KEEP_IN_PLACE |
| Podman 5.8.2 | installed/rootless | container runtime | ORACLE_FREE_TIER; KEEP_IN_PLACE |
| Mac Nexus bridge | active architecture, Mac-side authority | SSH loopback transport | HYBRID_MAC_ORACLE; KEEP_IN_PLACE |

No duplicate Oracle scheduler or competing state store was introduced.

## Ray-owned GitHub portfolio review

The current public portfolio was enumerated through GitHub's read-only API and
high-value repositories were inspected through available local clones or
repository metadata. `nexus-os-v2` is the canonical control plane; `nexuslive`
is a prior operational implementation; `nexus-mobile` is a client; Hermes is
upstream. Older numbered Nexus repositories and unrelated application/weather
repositories are not runtime sources for WP4 and are retained as references.

## Phase 0 decisions

New WP4 code must resolve capabilities in this order:

`NEXUS_ALREADY_HAS_IT → MAC_REPO_ALREADY_HAS_IT → ORACLE_ALREADY_HAS_IT → RAY_GITHUB_ALREADY_HAS_IT → HERMES_ALREADY_HAS_IT → MATURE_OPEN_SOURCE_ALREADY_HAS_IT → custom build`.

TruthKernel, authority, Keychain-dependent functions, deterministic Python,
and receipt authority stay Mac-local. Hermes, Ollama, SearXNG, and long-running
workers stay Oracle-local. Cross-node loops remain hybrid with Mac authority.

`MAC_REPOSITORY_DISCOVERY_COMPLETE=YES`
`ORACLE_REPOSITORY_DISCOVERY_COMPLETE=YES`
`RAY_GITHUB_PORTFOLIO_REVIEW_COMPLETE=YES`
`DUPLICATE_RUNTIME_IDENTITIES_RESOLVED_OR_DOCUMENTED=YES`
`PAID_RESOURCE_ACTIVATED=NO`
