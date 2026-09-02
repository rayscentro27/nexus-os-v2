# WP9F Oracle Hermes staging evidence

Reuse-before-install was satisfied: no image pull occurred. An isolated
ephemeral container was launched from the existing 0.20.6 digest with a 2 GiB
memory limit and no production environment file. It reported version,
Python/OpenAI SDK metadata, started supervised services, and exited 0 in
approximately 5.1 seconds. No container remained.

The existing production-adjacent container also exposed real `browser`,
`skills`, `tools`, `mcp`, `sessions`, and `gateway` CLI surfaces. Public browser
execution was proven in WP9E; this campaign did not invoke a model provider or
production messaging. Therefore:

- runtime startup/shutdown: `PASS_REAL`
- version/CLI/tool-surface: `PASS_REAL`
- model execution: `NOT_PROVEN_NO_MODEL_CALL`
- production cutover: `NONE`
- scheduler mutation: `NONE`
