# Nexus MCP volatile resource contract

Campaign: HG-WP6.6-HERMES-NEXUS-MCP-VOLATILE-FOLLOWUP-FRESHNESS-REPAIR-20260831-01

The six Nexus operational read capabilities are declared `VOLATILE`. A prior
conversation result may preserve referent identity, but it is not authoritative
for present/current/live state. A current-state request therefore requires a
fresh relevant MCP read. This is capability metadata and generic resource
guidance, not phrase routing or a conversational classifier.

Per-turn reuse is bounded to the active turn identifier. Cross-turn volatile
caching is not used. Failures are never cached.
