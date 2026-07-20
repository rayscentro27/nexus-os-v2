# Hermes OpenRouter Model Selection

Generated: 2026-07-20

## Decision State

Recommended primary model: `openai/gpt-5.6-luna`

Recommended backup model: `google/gemini-2.5-flash`

Activation state: `BLOCKED_PENDING_OPENROUTER_KEY`

This branch does not activate OpenRouter because no server-side `OPENROUTER_API_KEY` is available in the implementation worktree or process.

## Candidate Comparison

| Model | Input token price | Output token price | Tool support | Structured output support | Context | Estimated 30-turn cost | 100 turns/day | 500 turns/day |
|---|---:|---:|---|---|---:|---:|---:|---:|
| `openai/gpt-5.6-luna` | $0.000001/token | $0.000006/token | yes | yes | 1,050,000 | about $0.045 | about $0.15/day | about $0.75/day |
| `google/gemini-2.5-flash` | $0.0000003/token | $0.0000025/token | yes | yes | 1,048,576 | about $0.020 | about $0.07/day | about $0.33/day |
| `anthropic/claude-sonnet-4.5` | $0.000003/token | $0.000015/token | yes | yes | 1,000,000 | about $0.12 | about $0.40/day | about $2.00/day |

Cost estimates assume roughly 1,000 input tokens and 600 output tokens per turn. Actual costs must be recorded from provider usage metadata.

## Selection Reason

`openai/gpt-5.6-luna` is the recommended primary because OpenRouter metadata reports support for tool calls, tool choice, response formats, structured outputs, and a large context window. `google/gemini-2.5-flash` is the recommended backup because it supports the same required control parameters at lower cost.

## Required Ray Review Before Activation

- Add `OPENROUTER_API_KEY` only to server-side hosting secrets.
- Set `HERMES_OPENROUTER_MODEL=openai/gpt-5.6-luna`.
- Set `HERMES_OPENROUTER_BACKUP_MODEL=google/gemini-2.5-flash`.
- Confirm daily limit `$0.50` and monthly limit `$10.00`.
- Run provider health, tool-call, and structured-output smoke tests before enabling `RAY_ONLY_PILOT`.
