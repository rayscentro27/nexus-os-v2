# Hermes Langfuse repaired trace proof

Local Langfuse traces retained parent/child correlation, session metadata,
selected tools, MCP result fingerprints, currentness/support diagnostics, and
no chain of thought. Representative patched traces include:

- `d3583594271ec1bb4ee7d75ae6f8b40c`: opportunity read, supported fresh MCP
- `31b0fd21e14d2076faade6be687cb52a`: opportunity follow-up, supported fresh MCP
- `05b34ab9928175e237a7b8d84bacc85f`: review read, supported fresh MCP
- `6e813abfbca7d5047ea56132b98c3188`: prior-context diagnostic showing an
  unsupported claim when no fresh result existed

Remote Langfuse export and end-to-end correlation were certified in the prior
campaign and were not altered here.
