# Nexus MCP freshness preflight

## Static results

- Six Nexus capabilities declare `VOLATILE` freshness metadata.
- Generic current-state guidance is injected without phrase-specific routing.
- MCP receipts include `turn_id`, optional `update_id`, currentness, source,
  status, item count, and deduplication state.
- Per-turn successful duplicate reads are collapsed; cross-turn reuse is not.
- `services/nexus_mcp/tests/test_server.py`: 11 passed.
- Python compilation and diff checks: passed.

## Live status

The required Hermes primary two-turn regression could not execute on this host.
The Hermes venv lacked a usable provider runtime: the `openai` package was
initially absent, and after environment repair its import remained inconsistent
(`openai.types.responses.response_computer_tool_call` missing). Therefore the
following live criteria are unproven and readiness is `NO`:

`SECOND_TURN_NEXUS_GET_REVIEWS_EXECUTED`, `B2_FRESH_NEXUS_BLOCKER_READ`, and
`C2_FRESH_NEXUS_OPPORTUNITY_READ`.
