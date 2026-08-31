# Hermes-Native Nova Shadow Implementation

**Status:** isolated development path created; live Telegram unchanged.

## Entrypoint

`scripts/nova/nova_hermes_shadow.py:run_shadow` lazily loads the installed
Hermes Agent checkout, uses the current `agents.nova.SOUL`, defaults to the
current `openai/gpt-4o-mini` baseline, and invokes Hermes `AIAgent` with bounded
toolsets. The implementation refuses to run unless
`NOVA_HERMES_NATIVE_SHADOW=true` and refuses primary mode.

## Scope

The shadow does not alter `scripts/nova/nova_telegram_worker.py`, the current
five-stage graph, model settings, live session, or launchd definitions. It is
independently switchable and rollback is simply omission of the flag.

## Proof status

The path was exercised with the approved OpenRouter baseline. A simple question
completed through Hermes with one model call and no tool. A Nexus capability-map
read completed through `nexus_read_shadow`; a bounded Alpha request completed
through `alpha_challenge_shadow` using the existing governed Alpha execution
path, returning an Alpha receipt and research job id. A native `delegate_task`
probe also completed and returned its result to the same Hermes conversation.

The real web tool was callable, but the configured provider returned HTTP 402;
page extraction reported that the current free backend is search-only. This is
an honest provider/configuration limitation, not a shadow-runtime success.
