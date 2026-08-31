# Nova / Hermes Native Runtime Audit

**Campaign:** HG-WP6.5-NOVA-HERMES-NATIVE-RUNTIME-VS-CUSTOM-STACK-AUDIT-20260831-01  
**Baseline:** d588bfc  
**Audit mode:** read-only; no Nova, Hermes, provider, prompt, or authority changes.

## Executive finding

Hermes Agent 0.20.6 is installed at `/Users/raymonddavis/.hermes/hermes-agent` and
its editable package metadata reports version `0.20.6` (source checkout
`cea87d9139044870752aafdcdf9ca253049ae175`). The Telegram Nova worker does not
import or enter that native agent runtime. It runs the repository's five-stage
Nova graph and calls `scripts/nexus_agent_platform/agents/nova.py:_call_model`.

The correct audit conclusion is not that Hermes should replace Nova. Hermes has
useful native primitives that overlap with Nova's custom model/tool loop, but
Nexus-specific truth, authority, privacy, cost, receipts, and work-order
semantics must remain custom. A selective future integration is safer than a
primary-runtime migration.

## Installed Hermes feature evidence

| Capability | Status | Evidence | Boundary |
|---|---|---|---|
| Version | AVAILABLE | `hermes_agent.egg-info/PKG-INFO`, version 0.20.6 | Installed Hermes checkout, not Nova's venv |
| Model routing/providers | IMPLEMENTED / AVAILABLE | `agent/*_adapter.py`, `agent/model_metadata.py`, credential/provider modules | Not used by Nova `_call_model` |
| Native tool calling | IMPLEMENTED / AVAILABLE | `run_agent.py` tool-call loop; `agent/tool_executor.py`; `model_tools.py` registry/dispatcher | Hermes uses provider tool calls; Nova uses text envelope parsing |
| Tool continuation | IMPLEMENTED / AVAILABLE | `run_agent.py:_execute_tool_calls*` and conversation loop | Not used by Nova |
| Sessions | IMPLEMENTED / AVAILABLE | `gateway/session.py`, `agent/conversation_loop.py`, session DB/prompt restoration | Nova has separate custom session/memory |
| Memory | IMPLEMENTED / AVAILABLE | `agent/memory_manager.py`, memory tool and prompt guidance | Not used by Nova's Telegram worker |
| Profiles / identity | IMPLEMENTED / AVAILABLE | Hermes prompt builder/system prompt and profile-aware gateway context | Nova embeds SOUL in repository code |
| Skills / AgentSkills | IMPLEMENTED / AVAILABLE | `skills/`, `agent/skill_utils.py`, skill tools and prompt builder | Nova has its own capability catalog |
| Workers / subagents | IMPLEMENTED / AVAILABLE | `tools/delegate_tool.py`, `run_agent.py`, worker-thread execution | Not Alpha integration by itself |
| Delegation | IMPLEMENTED / AVAILABLE | native `delegate_task` schema/dispatcher | Does not replace Nexus Alpha intake/authority |
| Handoffs | PARTIAL | delegation and gateway handoff support exist; no proven Nova-to-Alpha production handoff | Requires an adapter and lifecycle contract |
| Reasoning effort | NOT_PROVEN as a generic Hermes contract | No repository-wide `reasoning_effort` control was found in the installed runtime; model/provider adapters expose model-specific reasoning fields in places | Do not assume tiered effort exists uniformly |
| Multi-model / MoA | NOT_PROVEN as a primary-agent feature | `moa` appears in toolset/delegation exclusions, but no proven native Nova ensemble contract was identified | Optional future experiment only |
| Grounded citations | NOT_PROVEN as a native truth-verification contract | Web extraction and evidence tools exist; no native claim-verification authority equivalent to TruthKernel was identified | Keep Nexus/evidence validation custom |
| Web tools | IMPLEMENTED / AVAILABLE | `tools/web_tools.py`, `agent/web_search_registry.py`, provider registry | Provider health/configuration remains runtime-specific |
| A2A | NOT_PROVEN for this Nova deployment | No proven active Nova A2A path in the audited local runtime | Do not plan on it |
| Smart approvals | PARTIAL / SCOPED | tool guardrails and approval hooks exist, especially terminal/ACP paths | Not a substitute for Nexus approval authority |

“Available” here means proven in installed source/configuration, not proven as
available to the live Nova Telegram process.

## Current Nova runtime

`scripts/nova/nova_telegram_worker.py` imports the repository through `scripts/`,
constructs the five stages, and ultimately invokes `agents/nova.py`. The current
model path is:

```text
Nova graph
  -> _generate_response
  -> _call_model
  -> LlmGatewayAdapter
  -> direct OpenRouter HTTP when LITELLM_GATEWAY_ENABLED is false/unavailable
  -> configured HERMES_NOVA_MODEL (historically observed as openai/gpt-4o-mini)
```

Evidence: `scripts/nexus_agent_platform/agents/nova.py:2713-2746` and
`scripts/nexus_agent_platform/workflows/litellm_adapter.py:16-128`.

Nova's current custom resource path is:

```text
model text
  -> _extract_model_capability_request
  -> validate_model_request
  -> execute_shared_capability
  -> structured result appended to a follow-up prompt
  -> second _call_model
```

Evidence: `agents/nova.py:4347-4391`. It does not pass a native `tools` list
from Nova to the provider, and its direct fallback returns `tool_calls: []`.

## Comparison conclusion

The custom stack duplicates generic orchestration responsibilities already
available in Hermes: provider adapters, native tool schemas, dispatch,
continuation, session storage, memory, skills, and subagent delegation. It does
not duplicate Nexus's governed operational truth or authority correctly enough
to remove those components. The custom text-envelope protocol is also more
fragile than Hermes's native assistant `tool_calls` / tool-result loop.

This supports a future selective replacement, but not an untested cutover.

