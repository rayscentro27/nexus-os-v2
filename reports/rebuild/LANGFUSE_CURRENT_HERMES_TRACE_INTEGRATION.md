# Langfuse Hermes trace integration

`NovaTrace` in `scripts/nova/langfuse_runtime.py` creates one `nova.turn`
correlation per Telegram update. Child events cover intake, authorization,
context, generation, resource selection, MCP, synthesis, and delivery.

The trace ID and update ID are propagated to the Hermes child before MCP
discovery. No additional LLM call is introduced.
