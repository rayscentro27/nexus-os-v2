# Google MCP Canonical Preflight

## Protocol and implementation

- Server starts: PASS
- MCP initialize: PASS
- Tool discovery: PASS; six read tools
- Write tools exposed: NO
- Existing Google credentials: configured
- Google API dependencies: installed in canonical Hermes/Nexus environment

## Real read probes

- Gmail search: PASS
- Gmail message read: PASS
- Gmail thread read: PASS
- Calendar search: PASS
- Calendar event read: PASS
- Calendar availability projection: PASS

## Hermes-native probes

- Recent email question selected Gmail MCP: PASS
- Today’s meetings question selected Calendar MCP: PASS
- Calendar → casual coffee: PASS
- Calendar → Nexus blocker read: PASS
- Post-Google general reasoning: PASS

## Boundary

Nexus regressions and focused Google tests pass. Live Telegram certification
against Ray’s account remains pending and is not claimed here.
