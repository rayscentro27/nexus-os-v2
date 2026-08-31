# Nova Custom Deprecation Map

Nothing is safe to remove during the shadow campaign.

| Current component | File | Shadow replacement | Safe now | Remove after cutover |
|---|---|---|---|---|
| Direct model call | `scripts/nexus_agent_platform/agents/nova.py:_call_model` | Hermes provider/model runtime | NO | Only after parity and rollback window |
| Text capability envelope parser | `agents/nova.py:_extract_model_capability_request` | Hermes native tool calls | NO | Only after native telemetry parity |
| Custom continuation | `agents/nova.py:_generate_response` follow-up | Hermes tool-result loop | NO | Only after failure/retry proof |
| Generic fallback | `agents/nova.py:_advisory_fallback` | Tool-aware Hermes fallback | NO | Only after identity/context proof |
| Provider wrapper | `workflows/litellm_adapter.py` | Hermes adapter/provider layer | NO | Only after cost/secret/latency parity |
| Nova custom session/memory | current Nova memory helpers | Hermes session/memory selectively | NO | Only after stale-belief migration proof |

