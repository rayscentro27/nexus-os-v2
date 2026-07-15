# Controlled Pilot Execution

## Run metadata

- Starting commit: `68070d352bb0337fab07a5e54260f99979161c0f`
- Fixture version: `controlled-pilot-v1`
- Personas: synthetic A, B, C only
- Session references: `synthetic-pilot-A`, `synthetic-pilot-B`, `synthetic-pilot-C` (sanitized references; protected IDs omitted)
- Browser: Chromium through Playwright
- Viewports: 1920×1080, 1366×768, 768×1024, 390×844
- Planned workflows: 12 checklist tasks per persona
- No passwords, tokens, document contents, report text, storage paths, signed URLs, or real PII were captured.

## Reset and replay

| Persona | Dry-run reset | Real reset | Full replay | Idempotency replay | Final workflow state |
|---|---|---|---|---|---|
| A | Pass; exact synthetic scope | Pass; selected scope only | Pass; verified | Pass; same bounded counts | Normal guided workflow |
| B | Pass; exact synthetic scope | Pass; selected scope only | Pass; verified | Pass; same bounded counts | Genuine exception; specialist review required |
| C | Pass; exact synthetic scope | Pass; selected scope only | Pass; verified | Pass; same bounded counts | Purchased-debt documentation workflow |

The reset resolved one exact synthetic Auth identity to one `goclear` client membership, preserved the Auth account, did not touch protected storage, and used child-first FK-safe deletion. Earlier interrupted synthetic sessions were marked `abandoned`; the current three controlled sessions were completed through the admin UI.

Replay verification found no active queued or processing duplicate jobs. A/B/C replay state included initial and follow-up documents, parser results, canonical data, strategy/readiness state, and persona-specific draft/decision/exception state.

## Tester sessions

Three current sessions were created with synthetic display names, the controlled fixture, build metadata, Chromium/device metadata, planned workflows, and closeout notes. Passwords were not stored. Current session outcomes: A completed, B completed, C completed.

## Planned task execution

The complete checklist is recorded in `controlled_pilot_task_checklist_latest.md`. The Playwright pilot covered login, comprehension, credit/exception flow, business requirements, inline upload, Documents Vault, Clyde, Funding Readiness, Request Review, feedback, session closeout, admin routing, and responsive behavior.

## External action boundaries

No email job was sent, no DocuPost request was submitted, no funding action was executed, and no approved fix was auto-executed. Ray Review remained approval-gated.
