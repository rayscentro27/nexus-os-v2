# Google MCP Security and Privacy

- Read-only MCP methods are the only registered Google tools.
- No send, draft, create, update, delete, reply, or invitation mutation tool is
  exposed.
- OAuth secrets remain in the existing keychain control plane.
- No Google content is forwarded automatically to Web, Alpha, Nexus truth, or
  Langfuse.
- Gmail output is bounded to metadata and short snippets.
- Calendar descriptions are omitted to avoid unnecessary PII and booking data.
- Errors return explicit unavailable/error envelopes; no data is fabricated.

`GOOGLE_DATA_AUTO_FORWARDED_TO_WEB=NO`
`GOOGLE_DATA_AUTO_FORWARDED_TO_ALPHA=NO`
`TRACE_DATA_MINIMIZATION=PASS`
