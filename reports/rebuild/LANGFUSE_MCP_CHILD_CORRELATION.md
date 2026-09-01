# MCP child correlation

The repaired controlled Nexus turn produced MCP receipts with non-null shared metadata:

- trace: `nova-langfuse-e2e-nexus-repaired-9b2201350c164fb6`
- turn: `shadow-turn-d9a3a0abe860`
- update: `langfuse-e2e-nexus-repaired`

Receipts contained request ids, tool names, canonical sources, currentness, item counts, dedupe state, and result status. The local parent trace recorded Nexus selection and a bounded result fingerprint.

The controlled turn executed 14 MCP calls, including successful per-turn deduplicated calls, and ended with an empty final response after the existing bounded synthesis/validation path. This campaign did not repair that behavior. Because no remote observation was found, cloud parent/child correlation remains unproven.
