# Hermes Response Renderer Contract

## Default: CEO / Jarvis

- Answer first, plain language, voice-ready.
- No raw repository paths, UUID dumps, access-control implementation detail, or debug route blocks.
- Keep structured advisory sections when they carry the decision, opportunity, validation, and risk contract.
- End with a safe next action or natural follow-up when useful.

## Audit mode

Triggered by `give me the audit version`, `show source details`, or equivalent.

Includes the prior answer plus route, intent/domain, sources, Supabase usage, timestamp, confidence, blockers, and assumptions. File paths remain available only in the underlying audit answer/source metadata.

## Trace mode

Triggered by source/provenance questions and explicit trace commands.

Explains route, intent, source list, model/Supabase usage, assumptions, and confidence. It does not expose hidden chain-of-thought.

## Casual mode

Returns simple common conversation without Nexus records, operational state, or stale advisory/session context.

## Action proof

Conversation-only drafts must retain their proof even in CEO mode:

- target
- review reason
- source
- proposed decision
- next safe action
- not saved
- not submitted
- not executed

## Rerendering

Response-depth commands target `lastAnswer` in scoped decision memory. They do not rerun the original domain route or permit an active session to hijack the request.
