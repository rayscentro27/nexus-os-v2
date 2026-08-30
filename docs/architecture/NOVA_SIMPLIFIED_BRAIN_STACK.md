# Nova Simplified Brain Stack

The target is a five-stage Nova runtime. The original conversational core from
`a962c19` remains intact; only the intercepting shell is simplified.

1. **Pre-model boundary** — authentication is owned by Telegram ingress;
   Nova combines utility handling, intent metadata, and strict governed-command
   checks here. It does not force a source for ordinary advisory/research turns.
2. **Context and capability plan** — one compact information plan and
   descriptive capability catalog are added to bounded session/company context.
3. **Model response** — Nova reasons first and may form an initial view before
   deciding which listed resource would help. The broker itself does not execute.
4. **Truth validation** — deterministic validators check retrieved claims,
   execution claims, freshness, and authority after evidence is present.
5. **Composition** — Nova preserves session continuity, plain-language output,
   and delivery metadata.

Existing shared capability handlers remain the invocation boundary for any
future model-selected tool. Nexus remains authoritative for operational reads
and requests; public research is not made dependent on Nexus health.

The current graph is five nodes: `pre_model_boundary`, `build_context`,
`generate_response`, `validate_output`, and `compose_output`.
