# Current defect observability evidence

The bounded local trace schema exposes session-turn count, prior assistant/tool result counts, prior volatile claim count, profile hash, tool availability, selected resource type, and deterministic claim-source diagnostics. It intentionally captures no chain-of-thought.

The available trace evidence is sufficient to distinguish a no-tool decision from a tool decision and to identify prior volatile context when present. MCP receipts carry request id, trace id, turn id, update id, currentness, canonical source, item counts, filtered counts, status, dedupe, and receipt hash.

The observed controlled MCP failure occurred before a successful Nexus result. Consequently this campaign does not claim evidence for the known freshness/referent defect and does not repair it. The next debugging campaign should first correct/prove the active MCP executable path, then compare fresh MCP metadata with prior-session metadata under the same parent trace.
