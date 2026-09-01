# Google ↔ Hermes referent continuity

Campaign: HG-WP7.1-GOOGLE-MCP-INTEGRATED-HERMES-PREFLIGHT-TO-LIVE-READINESS-20260901-01

The current Hermes-native runner exposed the Google MCP tools alongside Nexus,
Web, and Alpha. Google tool records are now classified as the `GOOGLE`
resource family. Resource-backed history is retained as referent metadata and
not as authoritative factual prose. A bounded event/message snapshot is kept
for anaphoric follow-ups; message bodies and calendar descriptions are not
included.

Calendar sequence exercised:

* “What meetings do I have today?” selected `mcp_google_mcp_calendar_search_events`.
* “Which one is first?” selected the same Calendar capability and remained in
  the Google Calendar domain. The live account returned zero events today, so
  there was no event identity to resolve.
* “What is it about?” remained in Calendar context and returned the truthful
  empty result.
* A general recurring-revenue question used no tool.
* “When is my next meeting?” performed a fresh Calendar read.

Gmail sequence exercised:

* Gmail search returned real authorized mailbox metadata.
* “Which one looks most important?” remained in Gmail context.
* “What was that thread about?” selected `gmail_read_thread` with the linked
  thread identifier and bounded metadata.
* A general partnership question used no tool.

Conclusion: Google referent metadata is generic and resource-scoped; it does
not create a persistent Google mode. Same-turn Gmail duplicate search requests
were observed in one model continuation and remain an efficiency observation,
not a change to truth semantics.
