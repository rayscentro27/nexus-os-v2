# Hermes / Nova Communication Benchmark — Sprint 0 WP0-E

## Purpose

Establish a reproducible baseline for understanding, context retention,
truthfulness, natural conversation, conciseness, follow-up awareness, status
explanation, error explanation, actionability, and voice readiness.

## Reproducible test set

1. Ask what is true about the current rebuild state.
2. Ask what happened after a bounded safe process completes.
3. Ask what happens next and whether Ray is needed.
4. Present a failed or unavailable dependency and request an explanation.
5. Ask for a concise operational summary with evidence paths.
6. Ask a follow-up that depends on the prior context.
7. Ask the system to distinguish configured, loaded, running, responding, and
   verified.
8. Ask for the next safe action without authorizing a consequential action.

Each case records the exact prompt, raw response in a protected local test
artifact if permitted, evidence references, and deterministic checks for
truthfulness/actionability. Subjective Ray observations must be labeled
separately from measured results.

## Baseline status

`NOT_SCORED` — no new external conversation or voice test was run in this
bootstrap package. Existing reports may be reviewed as historical context but
cannot establish a fresh benchmark score. The target remains
`HERMES_TARGET >= 9/10`; no score is fabricated.

## Next safe action

Run the reproducible set against the existing local Hermes/Nova path only
after confirming the invocation is bounded and does not send external
messages, alter profiles, or upgrade the runtime. Record limitations if the
local version/configuration cannot be confirmed.
