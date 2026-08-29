# Hermes Bot Mode Certification — 2026-08-29

`BOT_MODE_NATIVE=YES` is supported by the pinned gateway/worker architecture.
The native entrypoints are `hermes gateway run/start` and the Kanban worker
dispatcher. State is profile/session based and persistent under isolated
Hermes data. Tool access is task-scoped, but Kanban lifecycle tools are
injected into workers.

`HERMES_BOT_MODE_CERTIFIED=YES_WITH_SCOPED_PROVIDER`.
Oracle `gemma3:4b` remains the private reasoning route and rejects injected
Kanban tools. The dedicated `nexusopenrouter` profile uses the existing
zero-priced OpenRouter route and completed a bounded worker canary with
lifecycle-tool use, result comment, review handoff, and governed completion.
The worker remained complete after a Hermes container restart. No external
side effect or Nexus authority mutation occurred.
