# Nexus MCP live failure repair

No application repair was performed in this forensic pass. The evidence proves
that the live MCP currentness layer was correct while Hermes later omitted
fresh Nexus reads and reused volatile session content. Currentness filters were
therefore intentionally left unchanged.

The narrow follow-on repair must enforce generic volatile-resource freshness at
the Hermes/MCP capability boundary, preserve referent identity separately from
truth, and ensure live receipts receive the turn/update correlation before MCP
discovery. It must not use phrase routing or change Nova conversation behavior.
