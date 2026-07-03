# Hermes Alpha Ollama Provider Plan

## Decision

Do not require Ollama Pro now. Start with mock, then evaluate `ollama_local` using a small non-sensitive benchmark. Ollama is MIT-licensed and supports a local API; current official pricing lists Free, Pro, Max, and future Team plans. A paid cloud plan may help with larger research/synthesis tasks, but only after quality, privacy, limits, and cost behavior are measured.

## Task placement

- Ollama candidates: source summarization, opportunity comparison, campaign variants, strategy-spec critique, report synthesis.
- Stay mock/local deterministic: routing, scoring, safety, action eligibility, cost gates, source order, Ray Review proposals, trade/publish/send blocks.
- Never send client data or secrets to a provider.

## Provider contract

Supported future values: `mock`, `ollama_local`, `ollama_cloud`, `openrouter`, hosted/self-hosted custom. Fields: base URL, API key, model, request ID, input/output size, latency, estimated cost, external-call status, and error. Secrets remain environment-only.

Cost guard defaults to `$0/day`; external models are disabled. A future activation requires a nonzero Ray-approved budget, per-request ceiling, daily hard stop, redacted logging, and no fallback that silently spends money.

## Activation sequence

1. Mock provider and tests pass.
2. Create a fixed public-data evaluation set.
3. Run Ollama local manually with no sensitive context.
4. Compare accuracy, structured-output compliance, latency, and hardware cost.
5. Ray reviews cloud privacy/terms and Pro value.
6. Enable one provider in a development-only environment with a tiny cost cap.
7. Add usage ledger and kill switch before broader use.

Alpha remains objective/model/research-first because provider output is one input to the brain; local storage and future databases never outrank Ray's objective or the brain contract.
