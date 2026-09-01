# Partial multi-resource failure proof

The deterministic Google MCP server returns an explicit read-only error
envelope with empty items when OAuth/API access fails. It never fabricates
messages or events. Existing Nexus and Google adapters preserve independent
resource status, so a failed resource can be reported while valid results from
the other resource remain usable.

The server’s bounded failure tests pass. Live credential-preserving failure
injection was not performed against the production account; no credentials
were altered.
