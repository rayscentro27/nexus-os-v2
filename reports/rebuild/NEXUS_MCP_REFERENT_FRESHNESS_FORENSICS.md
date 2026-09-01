# Nexus MCP referent freshness forensics

For `Which of those are still active?`, the preceding user turn was an
opportunity query, but the response discussed blockers. The receipt has no
fresh `nexus_get_opportunities` call and returned blocker-shaped prose.

Conversation history could identify the referent, but it was allowed to supply
volatile truth. The required precedence is:

`FRESH_CANONICAL_MCP_STATE > PRIOR_SESSION_STATE`.

The failure is `STALE_CONTEXT_OVERRIDE` / `NO_FRESH_MCP_READ`; it is not an
opportunity currentness-filter failure.
