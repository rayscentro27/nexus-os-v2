# WP9K Delegation Evidence

The initial Hermes request produced a reasoned opportunity response but no
specialist assignment. After the boundary was added, Hermes registered the
tool but attempted the generic `tool_call` wrapper; Hermes rejected that form
because the MCP tool was directly callable. A bounded direct-call retry timed
out without a completed model-driven delegation receipt.

The direct MCP boundary test later completed and produced delegation receipt
`nexus-delegation-a8ffa4c415f644e39ea0f676c47e20f0`, but that is not equivalent
to Hermes deciding to delegate. Therefore:

`ORACLE_HERMES_DELEGATION=NOT_PROVEN`.
