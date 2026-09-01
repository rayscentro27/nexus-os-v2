# Current runtime remote trace proof

Controlled current Hermes-native Nexus turn:

- trace: `b23345beef0f0898f6582ffe44c1ebda`
- turn: `shadow-turn-d9a3a0abe860`
- session: `langfuse-nexus-remote-proof-session` (hashed in trace metadata)
- MCP receipts: non-null shared trace/turn/update identifiers

Remote lookup succeeded. Eight observations were returned under the same trace, including `telegram.intake`, `nova.session_context`, Hermes generation observations, `nexus.mcp`, `hermes.final_synthesis`, and `nova.turn.complete`. The controlled equivalent did not perform Telegram delivery, so a delivery observation is verified by instrumentation but not present in this direct run.
