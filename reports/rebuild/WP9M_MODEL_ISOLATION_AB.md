# WP9M Model Isolation

Only the `nova_nexus` profile model changed from
`nvidia/nemotron-3.5-lightning:free` to the existing authorized
`openai/gpt-4o-mini` OpenRouter route. Hermes, container, MCP, skills,
specialist contract, authority, and transport were retained.

Nemotron: single/sequential calls had passed, but multi-step behavior included
120-second timeouts and inconsistent tool selection. gpt-4o-mini completed the
bounded specialist, sequential, and multi-step probes in 37.19s, 27.21s, and
38.16s respectively. A first current-state single-tool probe returned malformed
output, so reliability is improved but not perfect and the single-tool gate is
not fully certified.

`MODEL_ISOLATION_RESULT=GPT4O_MINI_ACCEPTABLE_WIN`.
