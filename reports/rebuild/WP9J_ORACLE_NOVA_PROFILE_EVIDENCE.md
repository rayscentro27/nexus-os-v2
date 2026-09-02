# WP9J Oracle Nova profile evidence

## Result

The existing Oracle Hermes 0.20.6 service and the `nova_nexus` multiplex route
are healthy after the profile authentication repair. A bounded request through
`/p/nova_nexus/v1/chat/completions` returned `WP9J_PROFILE_MODEL_OK` after a
service restart. This proves profile-scoped model execution, not Nova's full
company-agent behavior.

Evidence:

- container: `nexus-hermes-0206`, existing container, Hermes `0.20.6`
- profile health: HTTP 200
- profile model list: HTTP 200, model id `nova_nexus`
- profile model request: HTTP 200, 8.15 seconds, exact sentinel returned
- profile `.env`: mode 600; provider key reconciled to the canonical Oracle
  OpenRouter key by hash without exposing its value

`NOVA_ON_HERMES_0206_PROFILE=NOT_PROVEN_FULL_IDENTITY`

The longer identity request did not complete within the bounded local command
window. No claim is made that the returned profile used the intended SOUL,
skills, MCP, or delegation behavior.

