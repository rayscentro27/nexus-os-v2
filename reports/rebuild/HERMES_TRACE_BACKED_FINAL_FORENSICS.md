# Hermes trace-backed final forensics

Campaign: HG-WP6.6-HERMES-NEXUS-TRACE-BACKED-REPAIR-TO-FINAL-PREFLIGHT-20260831-01

The direct Nexus truth probe returned reviews=0, blockers=0, opportunities=0,
work items=1. Langfuse traces showed A2, B2, C1, C2, and D1 using fresh MCP
results; D2 used no tool and was an opinion about the fresh review result.

Trace-backed repair evidence: `05b34ab9928175e237a7b8d84bacc85f`,
`607e9fa33c35f2ccb5b3c838350e886f`, `d3583594271ec1bb4ee7d75ae6f8b40c`,
`31b0fd21e14d2076faade6be687cb52a`.

The remaining observed issue before the final scoped change was semantic
follow-up widening: an anaphoric opportunity follow-up could request unrelated
Nexus reads. The repair carries the last capability from structured provenance
and scopes only that generic anaphoric follow-up to it.
