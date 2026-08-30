# Nexus Mac Reasoning Capability Inventory

Campaign: `HG-WP6.5-HERMES-INTELLIGENCE-STACK-RECONCILIATION-20260830-01`  
Mode: read-only audit; no installs, routing changes, service changes, or model changes.

## Resource baseline

The Mac Mini reports 8 GiB RAM, 4 logical CPUs / 2 physical cores, approximately 658 GiB free on the root volume, and load near 1.9 at capture. This is adequate for lightweight orchestration and deterministic control work, but not a good home for another browser-heavy or multi-service reasoning stack.

## Relevant local repositories

| Repository | Path | Remote / commit | Installed or running evidence | Capabilities | Disposition |
|---|---|---|---|---|---|
| nexus-os-v2 | `/Users/raymonddavis/nexus-os-v2` | `rayscentro27/nexus-os-v2` / `e56cc2d` | canonical working tree | TruthKernel integration, loops, skills, Telegram bridge, Python adapters | KEEP_IN_PLACE |
| nexus-ai | `/Users/raymonddavis/nexus-ai` | `rayscentro27/nexuslive` / `ec879d2` | local repo | older operating/control-plane patterns | WRAP / REFERENCE_ONLY |
| nexus-ai-worker | `/Users/raymonddavis/nexus-ai-worker` | `rayscentro27/nexuslive` / `246f3d6` | local repo | worker/delegation patterns | REFERENCE_ONLY |
| nexuslive | `/Users/raymonddavis/nexuslive` | `rayscentro27/nexuslive` / `4fb57df` | local repo | older operational implementation | WRAP / REFERENCE_ONLY |
| nexus-hermes-runtime | `/Users/raymonddavis/nexus-hermes-runtime` | `NousResearch/hermes-agent` / `3c27eb623` | local source; separate Mac Hermes runtime also running | Hermes upstream runtime | REFERENCE_ONLY; Oracle is canonical |
| nexus-mobile | `/Users/raymonddavis/nexus-mobile` | `rayscentro27/nexus-mobile` / `127df9f` | local repo | client/mobile interface | KEEP; no control-plane authority |
| nexus-oracle-api | `/Users/raymonddavis/nexus-oracle-api` | no remote / `6e74ea9` | local repo | Oracle integration/API patterns | WRAP |
| nexus-os-v2-brain-bakeoff | local isolated branch | `rayscentro27/nexus-os-v2` / `1f8db7b` | isolated research branch | Hermes language/brain experiments | REFERENCE_ONLY |
| nexus-os-v2-hermes-cert | local isolated branch | `rayscentro27/nexus-os-v2` / `94a5fb3` | isolated certification branch | Hermes acceptance evidence | REFERENCE_ONLY |
| nexus-os-v2-hermes-language | local isolated branch | `rayscentro27/nexus-os-v2` / `aac2675` | isolated language branch | response/language experiments | REFERENCE_ONLY |

No evidence supports importing a competing scheduler or control plane. `nexus-ai`, `nexuslive`, and `nexus-ai-worker` overlap with the current loop/worker layer and should remain reference or wrapped components until a specific capability gap is demonstrated.

## Installed packages and local state

The `.venv-agent-platform` environment has an importable LangGraph 1.2.10, Langfuse, Temporal, and Playwright path according to current environment/report evidence. LangChain, LlamaIndex, DSPy, Crawl4AI, PydanticAI, and LiteLLM are not importable there. `requirements-agent-platform.txt` declares several of these as intended dependencies, so declaration is not treated as installation proof.

`~/.crawl4ai` contains database/cache state from earlier work, while the canonical agent-platform environment does not import Crawl4AI. Prior reports document a bounded remote Crawl4AI adapter and a failed/unproven direct Mac Chromium path. This is evidence for wrapping an existing boundary, not for claiming a local active package.

Current launchd/process evidence includes the canonical Telegram bridge, Active Operator, Oracle tunnel, Mac Hermes gateway, Nova legacy worker, and recovery checks. Active Operator remains governed by its existing canonical state; this audit changes nothing.

## Ray-remembered tools

1. **LangGraph** — proven by the installed `.venv-agent-platform` import and current `graph_adapter.py`/modernization reports. It was introduced for stateful Hermes/Alpha/Nova graph orchestration. It is currently flag-gated, not consistently used by the canonical Telegram route. Use as a wrapper around Nexus authority, not as an authority source.
2. **Crawl4AI** — proven by `~/.crawl4ai` state and prior adapter/capability reports. It was introduced for public-page extraction after search. It is not importable in the canonical agent-platform environment and direct Mac browser execution was not certified. Keep the bounded remote adapter as a candidate for Research Alpha.

The exact historical installation date and the claim that both were installed specifically by Ray cannot be independently proven from the current repository; that uncertainty is retained.

## Current architecture finding

The live bridge is `scripts/telegram/nexus_telegram_bridge.py`. It runs deterministic Nexus pre-routing first, then optional `try_hermes_platform()` when feature flags enable it, then the WP5 router and legacy fallbacks. The Hermes graph itself is built from front-brain classification, context resolution, mode routing, capability execution, and response composition, but graph/platform flags default off. This explains why a Hermes-capable component exists without proving that every Telegram answer uses it.

Classification of the current answer path: **HYBRID**, with the canonical operational path behaving primarily as a deterministic router/template renderer and Hermes/LangGraph being partial, flag-gated fallbacks. Current cross-source reasoning and executive synthesis are not proven on the canonical WP5 path. Memory/session continuity is proven in Hermes foundation work, but not proven as consistently attached to every current Telegram department route.

