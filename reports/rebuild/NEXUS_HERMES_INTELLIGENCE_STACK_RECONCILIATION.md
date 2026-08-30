# Hermes Intelligence Stack Reconciliation

Campaign: `HG-WP6.5-HERMES-INTELLIGENCE-STACK-RECONCILIATION-20260830-01`  
Status: **AUDIT COMPLETE — IMPLEMENTATION DEFERRED FOR RAY REVIEW**  
Scope: read-only repository, runtime, capability, resource, and architecture audit.

## Executive finding

Nexus already has the important ingredients, but they are not one coherent intelligence path. The canonical Telegram bridge is a mixed system: deterministic pre-routing and department renderers handle the main WP5 route; a LangGraph/Hermes front-brain path exists but is flag-gated; legacy fallbacks remain loaded. Consequently, Hermes can reason in isolated paths while Telegram still produces mechanically correct but shallow answers.

The recommended architecture is a governed hybrid: Nexus/TruthKernel supplies authoritative facts and capability policy; Hermes 0.20.6 supplies conversational understanding and final explanation on Oracle; the existing LangGraph wrapper supplies explicit stateful multi-step orchestration; deterministic Nexus adapters execute and validate; Telegram remains only the communication surface.

## Current Telegram/Hermes trace

Observed source path:

`Telegram → nexus_telegram_bridge.py → deterministic Nexus pre-route → optional try_hermes_platform() → process_with_new_router() → legacy classifier/direct answer fallback → Telegram receipt/send`.

The platform path is gated by `NEXUS_AGENT_PLATFORM_ENABLED` and `NEXUS_HERMES_LANGGRAPH_ENABLED`; flags default off. `try_hermes_platform()` loads Hermes context and persistent conversation context, constructs an `AgentState`, invokes the Hermes graph, saves capability results for follow-up provenance, and optionally records tracing. The graph's front brain classifies conversation/advisory/operational reads/governed actions, but the canonical route does not consistently reach it.

| Stage | Current evidence |
|---|---|
| Intent understanding | PARTIAL: deterministic pre-router and optional front brain |
| Multi-step planning | PARTIAL: Hermes/Alpha/Nova graph nodes exist; canonical WP5 use not proven |
| Tool selection | PARTIAL: deterministic capability routing dominates; tool-capable Hermes exists on Oracle |
| Cross-source reasoning | NOT_PROVEN on canonical Telegram route |
| Result synthesis | MIXED: department/template renderers plus Hermes direct/graph fallbacks |
| Plain-language response | PARTIAL; WP6.5 real tests exposed shallow/generic answers |
| Hermes memory | PROVEN in Hermes foundation; not consistently attached to every Telegram route |
| Hermes session continuity | PARTIAL in platform context store; canonical-route coverage not proven |
| Hermes Kanban/workers | PROVEN foundation; not evidence that every Telegram request uses them |
| Authority | TruthKernel/Nexus remains authoritative; no authority transfer found |

Current answer-path classification: **HYBRID, operationally dominated by deterministic formatter/template behavior**. The source audit found no evidence that Hermes is currently the reliable cross-source executive reasoning layer for every Telegram request.

## Hermes native capability reconciliation

| Feature | Available | Current Nexus/Telegram use | Would help? | Disposition |
|---|---|---|---|---|
| profiles | YES / proven | Oracle foundation; route-specific use partial | Yes for bounded role context | USE_EXISTING_INSTALL |
| sessions | YES / proven | Hermes context store and WP foundation | Yes for follow-up context | WRAP |
| memory | YES / proven | foundation; Telegram coverage partial | Yes, if scoped to sanitized context | WRAP |
| skills / AgentSkills | YES / proven | WP4/WP5 skill layer | Yes, as capability instructions | USE_EXISTING_INSTALL |
| Bot Mode | YES / proven | bounded worker route | Yes for safe background work | WRAP |
| Kanban/workers/handoffs | YES / proven | Active Operator/worker paths | Yes for governed work, not casual chat | USE_EXISTING_INSTALL |
| tool invocation | YES / scoped provider | worker certification | Yes, behind Nexus allowlists | WRAP |
| model routing | YES / scoped | Ollama private reasoning and OpenRouter tool route | Yes, route by workload | WRAP |
| gateway/API | YES / proven | Oracle Hermes runtime | Yes | KEEP |
| routines/scheduled behavior | AVAILABLE through Nexus/Temporal/Active Operator | not a Telegram conversational dependency | Yes for future proactive briefs | DEFER |
| MCP/browser/web | PARTIAL / boundary-dependent | existing bounded adapters | Only for specific public research gaps | DEFER / WRAP |

Conclusion: **ARE_WE_UNDERUSING_HERMES_NATIVE_FEATURES=PARTIAL**. The underuse is mainly at the boundary between Telegram requests, verified evidence, and Hermes synthesis—not a need to replace the runtime.

## Architecture comparison

Scores below are design assessment from the observed implementation, not live certification. They are included to make tradeoffs explicit.

| Architecture | Intent | State grounding | Cross-source reasoning | Debuggability | Privacy/security | Authority compatibility | Resource fit | Overall |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A. Current deterministic router + renderer | 2 | 4 | 1 | 4 | 5 | 5 | 5 | 3.4 |
| B. Hermes-native only | 4 | 3 | 3 | 3 | 4 | 4 | 4 | 3.6 |
| C. Hermes + existing LangGraph + Nexus broker | 5 | 5 | 5 | 4 | 5 | 5 | 4 | 4.7 |
| D. Existing Alpha/Nova installed stack alone | 4 | 3 | 4 | 3 | 4 | 4 | 4 | 3.7 |
| E. New full external agent framework | 4 | 2 | 4 | 2 | 2 | 2 | 2 | 2.6 |

The weighted recommendation is C because it addresses semantic understanding and evidence synthesis while keeping facts, authority, credentials, and execution deterministic. Feature count alone is not the deciding factor.

## Research Alpha recommendation

Current WP6 evidence remains: search acquisition PASS; primary-source page retrieval and verification NOT_PROVEN. The canonical upgrade should be:

`question → LangGraph stateful research plan → private SearXNG discovery → bounded Crawl4AI/public-page retrieval → primary-source preference → claim extraction/cross-check → Hermes synthesis → citations/confidence → TruthKernel receipt`.

GPT Researcher is a useful bounded pilot/reference for multi-source research, but should not become the general Telegram brain. Existing Crawl4AI remote/public URL boundaries should be reused first. A video path should extract claims/transcripts, identify creator incentives, independently verify claims, and classify `REAL`, `FALSE_OR_MISLEADING`, `VIABLE_WITH_MODIFICATION`, or `MORE_RESEARCH_REQUIRED`.

## Canonical recommendation

`Telegram → authenticated Nexus ingress → TruthKernel evidence/policy broker → Hermes 0.20.6 session on Oracle → existing LangGraph state graph when multi-step reasoning is needed → allowlisted Nexus capabilities → deterministic validation → FACT/ESTIMATE/ASSUMPTION/UNKNOWN result payload → Hermes executive synthesis → Telegram.`

Placement:

- **Mac:** TruthKernel, authority, Keychain-backed credentials, sensitive deterministic processing, lightweight graph coordination, receipts, canonical state.
- **Oracle:** Hermes, Ollama, SearXNG, bounded workers, public research extraction, heavier model/browser work.
- **Optional cloud:** none mandatory; only separately approved, privacy-reviewed, cost-reviewed routes.

Keep Nexus native control and receipts; wrap Hermes native sessions/skills/workers; wrap existing LangGraph and Crawl4AI boundaries; add a verified evidence broker and structured synthesis layer in a later implementation campaign; defer Langfuse self-hosting, Browser Use, Stagehand, DSPy runtime, LlamaIndex, Firecrawl, PydanticAI, and Microsoft Agent Framework until a demonstrated gap justifies them.

This solves the Telegram problem by separating routing truth from semantic interpretation and by making the response renderer consume a structured verified result rather than a status enum or receipt path. It improves Alpha by adding the missing page-retrieval and claim-verification stages without duplicating the whole research stack. It preserves authority because Hermes can recommend and explain but cannot mutate TruthKernel state, select unallowlisted executors, approve gates, send external communications, or perform prohibited actions.

## Proactivity and repeated intent — design only

Repeated semantic questions should be detected as an information need, matched to an existing loop, and proposed as a cadence or bounded brief. If no loop exists, Nexus should create a recommendation/work item; any consequential persistent behavior still requires the appropriate gate. No silent self-expansion is authorized.

## Deferred implementation sequence

| Phase | Work | Gate / rollback | Real pass criterion |
|---|---|---|---|
| A | Add evidence broker and Hermes synthesis to read-only Telegram path | WP6.5 continuation; retain deterministic route flag/rollback | fresh live status/repo/review answers grounded in receipts |
| B | Re-certify semantic Telegram E2E | existing WP6.5 authority | varied natural-language requests answered correctly |
| C | Upgrade Alpha with primary-page retrieval/verification | same gate only if bounded; new gate if cost/privacy expands | retrieved primary content, claim evidence, uncertainty |
| D | Reconcile Hermes/Alpha/Nova compound workflows | separate scope review if authority changes | cross-agent handoff and receipt proof |
| E | Repeated-intent/proactivity design and pilot | separate activation gate for persistent autonomy | explicit proposal, approval, bounded cadence, rollback |

No phase is implemented by this audit.

## State and limits

`WP6_5_STATUS_AFTER_AUDIT=OPEN_TELEGRAM_DEFECTS_RETAINED_FRESH_RETEST_REQUIRED`  
`WP6_6_READINESS=NOT_READY_PENDING_WP6_5_TELEGRAM_RETEST_AND_REASONING_ARCHITECTURE_REVIEW`  
`ACTIVE_OPERATOR=UNCHANGED_BY_THIS_AUDIT`  
`PAID_RESOURCE_ACTIVATED=NO`

Full repository and resource tables are in the companion reports. Candidate project references are in `NEXUS_OPEN_SOURCE_REASONING_RESEARCH.md`.
