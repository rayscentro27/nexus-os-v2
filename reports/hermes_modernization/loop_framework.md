# Nexus Loop Framework

Phase 4 adds a bounded, token-efficient loop runtime for two loops only:

- `system_health_loop`
- `opportunity_discovery_loop`

## Contract

A Nexus Loop is not an always-running model. Each run follows:

1. trigger
2. deterministic precheck
3. change detection
4. dedupe
5. deterministic processing
6. decide whether AI is materially necessary
7. lowest reliable model tier
8. verifier
9. bounded structured memory write
10. stop

If nothing materially changed and `stop_if_no_change` is enabled, the loop exits with zero model calls and zero model tokens.

## Enforcement

The runtime enforces:

- `deterministic_precheck`
- `delta_only`
- `cache_enabled`
- `dedupe_enabled`
- `max_ai_calls`
- `max_input_tokens`
- `max_output_tokens`
- `estimated_token_budget`
- `cost_ceiling`
- `model_tier`
- explicit premium escalation
- verifier
- retry limits
- `stop_if_no_change`
- structured bounded memory
- execution ledger

## Loop specs

### system_health_loop

Deterministic reads:

- system health
- process registry
- runtime execution summary
- pending approvals

Observed behavior:

- second identical run exits with `ai_calls = 0`
- second identical run exits with `tokens = 0`
- ledger records deterministic execution share

### opportunity_discovery_loop

Deterministic reads:

- opportunities
- recent research
- business model summary

Flow:

- collect
- normalize
- hash/dedupe
- compare against prior state
- deterministic scoring
- materiality threshold
- AI only for promising/new evidence
- verify
- structured opportunity candidate

Observed behavior:

- duplicate low-signal input stays zero-token
- promising new evidence can invoke the lowest reliable AI tier
- deterministic structure is preserved and AI synthesis is merged onto it

## Runtime outputs

Each run persists:

- structured loop state
- append-only execution ledger
- verified execution telemetry event

## Metrics tracked

- executions
- zero_token_executions
- ai_executions
- tier1_calls
- tier2_calls
- tier3_calls
- input_tokens
- output_tokens
- estimated_cost
- successful_outputs
- value_events
- tokens_per_success
- cost_per_success

## Memory policy

Loop memory is bounded and structured:

- history is truncated
- deltas are retained, not transcripts
- prompt text is not stored
- execution facts are written as JSON

