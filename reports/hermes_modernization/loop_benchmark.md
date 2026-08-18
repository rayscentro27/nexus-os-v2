# Nexus Loop Benchmark

This checkpoint uses the token-efficient loop runtime with temp-state runs and governed reads.

## Zero-token deterministic path

Sample run:

- `system_health_loop`
- repeated twice with identical inputs
- second run result:
  - `ai_calls = 0`
  - `zero_token_execution = true`
  - `estimated_cost = 0.0`
  - `estimated_cost_status = ZERO_PROVIDER_TOKEN_CHARGE`
  - `pricing_provider = none`
  - `pricing_model = no_model`

The second identical run stayed on the deterministic path and did not invoke AI.

## Duplicate-input opportunity path

Sample run:

- `opportunity_discovery_loop`
- duplicate opportunity payload
- result:
  - `ai_calls = 0`
  - `zero_token_execution = true`
  - canonical dedupe preserved

This proves duplicate input does not force a model call.

## AI-positive opportunity path

Sample run:

- `opportunity_discovery_loop`
- material opportunity payload
- result:
  - `ai_calls = 1`
  - `tier2_calls = 1`
  - `zero_token_execution = false`
  - `status = completed`
  - `verifier = pass`
  - `input_tokens = 535`
  - `output_tokens = 20`
  - `estimated_cost = 0.0015375`
  - `estimated_cost_status = ESTIMATED_FROM_CONFIG`
  - `estimated_cost_source = estimated`
  - `pricing_provider = openrouter`
  - `pricing_model = openai/gpt-4o`
  - `tokens_per_success = 555.0`
  - `cost_per_success = 0.0015375`

The AI result was merged onto the deterministic candidate set instead of replacing it.

## Cost accounting unit

- `estimated_cost` is **USD dollars**
- formula is normalized per million tokens:
  - `cost = (input_tokens / 1_000_000 * input_price_per_million) + (output_tokens / 1_000_000 * output_price_per_million)`
- verified unit check:
  - `T1_CHEAP_AI` via config: `_cost_for_tier("T1_CHEAP_AI", 163, 270) == 0.00018645`
  - `T2_STANDARD_AI` via config: `0.0015375` for `535 input / 20 output`
- local Ollama quote:
  - `estimated_cost = 0.0`
  - `estimated_cost_status = LOCAL_COMPUTE`
- unknown model quote:
  - `estimated_cost = null`
  - `estimated_cost_status = UNKNOWN`

## Observed timing

The loop runtime remains bounded in the deterministic path.
The AI-positive opportunity path completed quickly in this benchmark capture.

## Test suite observation

Focused tests:

- `22 passed`
- `0 failed`
- `0 skipped`

The current benchmark run confirms the phase 4/5 loop guardrails are operating as intended.
