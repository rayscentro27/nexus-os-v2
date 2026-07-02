# Hermes Advisory Continuity Patch

Generated: 2026-07-01 19:15 America/Phoenix

- Human-experience questions now use `casual_common` without Supabase, selection memory, or model calls.
- Tesla Model 3/Y and other product-model wording is separated from AI model usage/status wording.
- Plan-level follow-ups use a dedicated `advisory_followup` route and advisory state, separate from selection memory.
- Advisory state expires after six turns. Trace/casual turns do not overwrite it; explicit domains and entities override it.
- Nexus CRM/feature requests use planning-only `nexus_build_planning`. Explicit start/build-file requests are approval-gated and perform no implementation.
- Generic fallback is reached only after the safe advisor routes and both continuity mechanisms reject the message.
- 545/545 tests and the production build passed.
- Browser verification remains blocked by authenticated admin sign-in.
