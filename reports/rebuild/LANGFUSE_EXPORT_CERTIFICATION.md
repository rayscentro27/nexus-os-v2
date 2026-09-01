# Langfuse export certification

Campaign: HG-WP6.6-LANGFUSE-DIRECT-EXPORT-ROOT-CAUSE-AND-REMOTE-VISIBILITY-REPAIR-20260831-01

Remote export is proven for both the native SDK and the existing OTel adapter. The current Hermes-native Nova trace is remotely queryable, and the Nexus MCP observations share its valid Langfuse trace ID. MCP receipts retain request IDs, tool names, canonical sources, currentness, item counts, statuses, dedupe state, and bounded result fingerprints.

Fail-open, redaction, no-old-brain, no-A/B, and no-new-tracing-LLM-call checks passed. Conversation, Nexus freshness, referent selection, and tool behavior were not repaired.

`LANGFUSE_CERTIFIED_FOR_CURRENT_RUNTIME=YES`
`READY_TO_USE_LANGFUSE_FOR_HERMES_DEBUGGING=YES`

Next campaign: `HG-WP6.6-LANGFUSE-TRACE-BACKED-HERMES-VOLATILE-STATE-AND-REFERENT-REPAIR-20260831-01`
