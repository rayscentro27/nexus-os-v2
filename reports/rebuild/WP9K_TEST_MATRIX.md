# WP9K Test Matrix

| Area | Evidence | Result |
|---|---|---|
| MCP read surface | `services/nexus_mcp/tests/test_server.py` | 15 passed |
| Specialist allowlist/receipt | same suite | passed |
| HTTP auth | local 401 missing bearer; authenticated Streamable HTTP | passed |
| Oracle MCP | real `nexus_get_reviews` and `nexus_get_system_health` calls | passed |
| Oracle skill | real `system-operations` profile execution | passed |
| Hermes delegation | bounded model retry, no completed assignment | not proven |
| A/B / Telegram | correctly gated | not run |
| Scheduler | launchd authority/state inspected, untouched | preserved |

WP9 durable state observed during this phase remained `RETRY_NIGHT_1`.
