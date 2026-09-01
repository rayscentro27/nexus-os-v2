# WP8.11C Creative AI Path

## Scope

This report audits the WP8.11B generation path and records the WP8.11C model
route without changing the WP8.11B Creative core.

## WP8.11B trace

- `TERRITORY_GENERATION_SOURCE=RULE_BASED_GENERATOR`: `department.py` contains four fixed territory specifications.
- `COPY_GENERATION_SOURCE=DETERMINISTIC_TEMPLATE`: landing copy is assembled by `_html`; channel packages contain fixed angle strings.
- `SOCIAL_GENERATION_SOURCE=RULE_BASED_GENERATOR`: `create_channel_assets` emits fixed channel/count packages.
- `CRITIC_SOURCE=DETERMINISTIC_RULE`: genericness and render checks are repository code; no model call occurs.
- `REVISION_SOURCE=DETERMINISTIC_TEMPLATE`: landing v2 uses a fixed headline/CTA revision.

The zero count was therefore genuine: the WP8.11B E2E contains no model gateway
call and reports `ai_calls=0`; it was not an observability omission.

## Adapter

`scripts/nexus_agent_platform/creative/model_intelligence.py` adds a bounded,
provider-neutral Creative model adapter. It preserves deterministic authority
for state, claims, versioning, budgets, receipts, and external-action denial.
It requests concise JSON summaries and stores no chain-of-thought.

The existing Oracle Ollama service was reachable and advertised `gemma3:4b`,
but inference did not return a tiny probe within 120 seconds. The active
Hermes CLI also reported no configured LLM provider. Consequently the four
Creative calls were not certified and no fabricated AI artifacts were stored.

`REAL_CREATIVE_AI_INVOCATION=NOT_PROVEN`
`REAL_CREATIVE_DIRECTOR_REASONING=NOT_PROVEN`
`REAL_AI_COPYWRITER=NOT_PROVEN`
`REAL_AI_CREATIVE_CRITIC=NOT_PROVEN`
`REAL_AI_CREATIVE_REVISION=NOT_PROVEN`
`CREATIVE_AI_BUDGET_ENFORCED=YES` (`MAX_AI_INVOCATIONS=12`)

## Model route resolution

- canonical Hermes source inspected: `/Users/raymonddavis/nexus-hermes-runtime`
- Hermes version: `0.20.0`
- Hermes source commit: `3c27eb6234bf91b8ceee9e9071591b31e9b148cb`
- active CLI: `/Users/raymonddavis/.local/bin/hermes`, a separate user checkout
- canonical Hermes CLI invocation: no provider configured
- existing Nexus advisory route: Oracle Ollama `gemma3:4b`, remote execution
- cost class: configured zero-token-charge/private infrastructure route, but inference currently unavailable

The distinction is intentional: an advertised model is not treated as a
successful Creative model invocation.

