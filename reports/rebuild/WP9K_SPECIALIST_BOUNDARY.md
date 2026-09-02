# WP9K Specialist Boundary

`nexus_delegate_specialist` is a least-privilege MCP contract. It accepts a
bounded objective (500 characters maximum) and one of SYSTEM, ALPHA, FINANCE,
GROWTH, CREATIVE, JAX, or TRADING. Each name maps to a pre-existing canonical
read. It cannot execute shell, mutate state, publish, pay, trade, or alter
authority.

Unit tests cover rejection and allowlisted read-only receipts. An authenticated
Oracle-to-Mac MCP client discovered and invoked SYSTEM delegation successfully,
returned current system data, and persisted a hashed delegation receipt.

`SPECIALIST_BOUNDARY=PASS`. This does not certify Hermes model selection of
the tool.
