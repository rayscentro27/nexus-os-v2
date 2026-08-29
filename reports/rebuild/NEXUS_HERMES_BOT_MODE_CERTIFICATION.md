# Hermes Bot Mode Certification — 2026-08-29

`BOT_MODE_NATIVE=YES` is supported by the pinned gateway/worker architecture.
The native entrypoints are `hermes gateway run/start` and the Kanban worker
dispatcher. State is profile/session based and persistent under isolated
Hermes data. Tool access is task-scoped, but Kanban lifecycle tools are
injected into workers.

`HERMES_BOT_MODE_CERTIFIED=BLOCKED_PROVIDER_TOOL_COMPATIBILITY`.
Three distinct bounded attempts were made: local `gemma3:4b` rejected the
injected tool schema; a separate profile lacked a provider; and the existing
Groq credential was rejected with HTTP 403. No authority was expanded and the
synthetic tasks were archived. The route is fail-closed and ready for a future
approved compatible tool-capable provider.
