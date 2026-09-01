# Current Hermes trace proof

The controlled current Hermes-native greeting turn used the repository runner and dedicated profile with no Telegram delivery side effect. Trace id: `nova-langfuse-e2e-greeting-2-c88acfc9a8a3437b`; turn id: `shadow-turn-6455a83348b1`; session correlation is retained as a hash.

The local trace contains `telegram.intake`, `nova.session_context`, `hermes.generation`, `hermes.final_synthesis`, and `nova.turn.complete`. It records runtime `hermes`, model metadata, zero tools, no chain-of-thought capture, profile hash, and final latency. It does not prove a remotely visible Langfuse trace because the child Hermes venv does not have the Langfuse package and the parent/child exporter identity is not remotely verified.

The requested Nexus variant attempted MCP discovery but the profile configured `/Users/raymonddavis/nexus-hermes-runtime/.venv/bin/python`; the connection was cancelled. No Nexus state claim was accepted from that failed attempt.
