# Nova Live Brain Identity

Campaign: `HG-WP6.5-NOVA-LIVE-BRAIN-IDENTITY-MODEL-PATH-AND-RECOMMENDATION-FORENSICS-20260831-01`

The configured live Telegram path is:

`launchd → scripts/ops/run_nova_with_runtime_env.sh → scripts/nova/nova_telegram_worker.py --once → get_nova_graph() → five stages`

The live graph source is `scripts/nexus_agent_platform/agents/nova.py`. Its active model call is `_call_model`, using `LlmGatewayAdapter`. With the launch environment, LiteLLM is disabled and the adapter uses the existing OpenRouter direct endpoint. The model is `openai/gpt-4o-mini`.

The active profile is the concise embedded `SOUL` in `agents/nova.py`; no separate profile file is injected. The current SOUL is 1,637 characters in the normalized prompt inspection and had the same hash across the tested question classes.

The model receives the same graph/model path for general, advisory, current, Nexus, and Alpha turns, but pre-model factual company reads may execute the existing deterministic capability gate before model generation. Ordinary advisory/current prompts use `model_first` and receive an information plan, resource catalog, reasoning abilities, and the optional capability-envelope protocol.

The important limitation is execution, not identity: the model can request one bounded capability envelope, but receipts do not yet prove every live Telegram request selected or executed one. A plain model answer after no envelope is indistinguishable from a generic answer unless runtime telemetry is present.
