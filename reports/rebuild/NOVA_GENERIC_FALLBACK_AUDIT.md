# Nova Generic Fallback Audit

## Fallbacks found

1. `LlmGatewayAdapter._fallback_completion`: LiteLLM fallback to direct OpenRouter. In the current launch environment LiteLLM is disabled, so direct OpenRouter is the primary model route rather than a generic assistant.
2. `agents/nova.py:_advisory_fallback`: local deterministic fallback after model failure/empty response. It is topic-sensitive and contains generic provider-unavailable, research, Nexus-runtime, and governed-action text. It has no model, tools, or resource catalog.
3. `validate_output` fallbacks: deterministic truthful responses for validation failures. They do not invoke another model.
4. Telegram empty/error responses: worker-level delivery/error text after graph failure; no tools or resource awareness.

`GENERIC_FALLBACK_EXISTS=YES`.

Its trigger is model provider failure, empty content, validation failure, or worker exception. It does not know tools, Nexus, or Alpha beyond static text. This can explain generic/refusal responses when a model call or capability continuation fails, but existing receipts do not identify which fallback ran for the reported Telegram turns.
