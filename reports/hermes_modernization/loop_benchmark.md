# Nexus Loop Benchmark

This checkpoint uses the new loop runtime with temp-state runs and fake governed reads to measure policy behavior.

## Zero-token deterministic path

Sample run:

- `system_health_loop`
- repeated twice with identical inputs
- result:
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
  - `top_candidates` preserved

This proves duplicate input does not force a model call.

## AI-positive opportunity path

Sample run:

- `opportunity_discovery_loop`
- high-signal opportunity payload
- result:
  - `ai_calls = 1`
  - `tier1_calls = 1`
  - `zero_token_execution = false`
  - `status = completed`
  - `verifier = pass`
  - `input_tokens = 163`
  - `output_tokens = 270`
  - `estimated_cost = 0.2165`
  - `tokens_per_success = 433.0`

The AI result was merged onto the deterministic candidate set instead of replacing it.

## Observed timing

Combined sample run of:

- two `system_health_loop` runs
- one zero-token `opportunity_discovery_loop` run

Elapsed:

- `19.642s`

AI-positive opportunity run:

- `6.049s`

## Test suite observation

Focused loop tests:

- `8 passed`
- `0 failed`
- `0 skipped`

The pytest session on this machine is slow to tear down temporary directories, but the focused loop assertions are passing.

