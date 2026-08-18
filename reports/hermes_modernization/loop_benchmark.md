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
  - `estimated_cost = 1.3875`
  - `tokens_per_success = 555.0`
  - `cost_per_success = 1.3875`

The AI result was merged onto the deterministic candidate set instead of replacing it.

## Cost accounting unit

- `estimated_cost` is **USD dollars**
- verified unit check: `_cost_for_tier("T1_CHEAP_AI", 163, 270) == 0.2165`
- formula: `(163 + 270) * 0.0005 = 0.2165`

## Observed timing

The loop runtime remains bounded in the deterministic path.
The AI-positive opportunity path completed quickly in this benchmark capture.

## Test suite observation

Focused tests:

- `22 passed`
- `0 failed`
- `0 skipped`

The current benchmark run confirms the phase 4/5 loop guardrails are operating as intended.
