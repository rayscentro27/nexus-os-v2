# Gmail duplicate-search forensics

The original integrated probes showed repeated Gmail search tool messages in a
single model exchange. The model was retrying/reselecting discovery while the
result set was not available as native referent context. After the referent
repair, Turn B selected `gmail_read_thread` and did not issue a new Gmail
search.

The runtime now installs a task-scoped successful-read memoization wrapper on
the actual Hermes MCP registry names. Its key includes Hermes task ID, tool,
and canonical arguments, and is bounded. It cannot reuse a volatile result
across turns. Further production telemetry should distinguish duplicate model
tool messages from duplicate underlying API executions.
