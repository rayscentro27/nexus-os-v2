# Nova Conversational Core vs Outer Layers Audit

Campaign: `HG-WP6.5-NOVA-CONVERSATIONAL-CORE-VS-RESTRICTIVE-OUTER-LAYERS-AUDIT-20260830-01`

## Decision

`KEEP_NOVA_CORE_REBUILD_OUTER_LAYERS`

Confidence: `HIGH`.

The original Nova was created in commit `a962c19` as an isolated conversational
agent with its own SOUL, short-lived memory, LangGraph graph, OpenRouter model,
and Telegram worker. Its original prompt explicitly described natural
conversation, respectful disagreement, creativity, and continuity. It had no
Supabase, Nexus, Alpha, or business-tool access. That is the recoverable
conversational core.

Current Nova still uses that core, but later commits added deterministic
capability gates, canonical operational reads, domain/source policy, truth
validation, company-context injection, and fallback renderers around it.
Those outer layers are useful for authority and evidence, but they can run
before model synthesis and force a capability-specific failure into the final
answer.

## Current live path

`nova_telegram_worker.process_message` → authorization/mission/lock →
`get_nova_graph().invoke` → `classify_intent` → `handle_utility` →
`_capability_gate` → `_build_context` → model call → `_validate_output` →
`_compose_output` → Telegram delivery.

The graph is LangGraph-backed when the feature flag and import are available.
The worker supplies the live session metadata and Nova memory is loaded by the
graph. Nexus capability execution is centralized in
`capabilities/shared.py`; it is not the model's authority.

## A/B divergence

| Pair | Conversational A | Research/current B | First divergence |
|---|---|---|---|
| Affiliate | no capability or ordinary reasoning path | `_semantic_capability_gate` selects `public_web_search` | pre-model capability gate |
| SmartCredit fit vs find programs | model can reason from existing context | search is forced before synthesis | `_capability_gate` source selection |
| Tesla opinion vs current strategy | ordinary model response | public-web capability is forced | domain/capability gate |
| AI-agency definition vs $10k research | ordinary model response | public-web capability is forced | research/source gate |

For B requests the model does not receive an unencumbered conversational turn:
the capability result is attached first. When the web operation fails, the
response path can fall back to the bounded failure response rather than asking
Nova to choose an alternate authorized route.

## Proven web failure

The durable receipts show `hermes_search_20260830T202421Z` and subsequent
equivalent requests ending `all_providers_failed`, with provider `none` and
`No web search provider configured`, while the receipt also reports provider
identities `searxng, brave`. The failure is therefore in provider environment
resolution/availability at `phase15.live_research._load_web_search` →
`hermes_web_search._provider_priority` / provider invocation, not evidence that
the public web is conceptually forbidden to Nova. Earlier receipts on
2026-08-27 prove SearXNG succeeded, so this is a current runtime/provider
configuration or reachability failure, not a missing web implementation.

This audit does not manufacture a new live request. Exact lower-level network
cause is not proven by the receipt alone; the receipt proves the provider chain
returned no usable provider/result.

## Outer-layer findings

- `classify_response_mode` and utility handling help simple conversation.
- `_capability_gate` protects authority but selects tools before model reasoning.
- Domain policy correctly prevents Nexus from being universal, but it is still
  deterministic preselection rather than model-led information planning.
- Truth validation is necessary and should remain after evidence retrieval.
- Fallbacks correctly avoid unsupported claims, but some wording exposes an
  implementation failure as a broad inability.
- Report quarantine is protective and must remain.
- The shared allowlist protects direct Nexus writes; it should not block reads,
  public search, or bounded Alpha intake when those capabilities are available.

## Nexus dependency result

| Capability | Nexus required? | Classification |
|---|---|---|
| General conversation | no | accidental coupling if routed through company context |
| Public web search | no, except current adapter is housed in Nexus code | useful shared adapter; operational coupling is unnecessary |
| Page retrieval | no | Alpha/web dependency, not Nexus truth |
| Alpha | no | intentional specialist handoff |
| Model reasoning | no | accidental coupling when capability gate fails first |
| Sessions/memory | no | Nova-native |
| Tool discovery | no | shared capability registry is useful |
| Operational truth | yes | intentional TruthKernel authority |

## Contamination audit

Quarantine remains active in `report_quarantine.py`; synthetic, fixture,
development, legacy-unknown, and unknown-provenance reports are excluded from
current truth. The current company context may still include a derived daily
brief as context, so the future outer-layer rebuild must enforce quarantine at
context construction as well as at truth-view claim construction. No historical
report is evidence of live Telegram certification.

## Recommendation rationale

Option A (repair current brain) retains too many pre-model gates and has high
regression risk. Option C (new Nova V2) discards a working conversational core
and creates unnecessary migration and proof risk. Option B keeps the proven
conversation/session/model behavior while replacing the restrictive shell with
a capability broker that lets Nova understand the goal first, choose among
allowlisted resources, retrieve evidence, and validate claims afterward.
