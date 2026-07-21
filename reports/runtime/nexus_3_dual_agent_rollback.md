# Nexus 3 Dual Agent Rollback

Generated: 2026-07-21

Rollback was not executed because the Ray-only frontend was not deployed.

Expected rollback remains:

- `VITE_HERMES_MODEL_FIRST_MODE=OFF`
- `VITE_ALPHA_MODEL_FIRST_MODE=OFF`

This should return both agents to prior production behavior without deleting conversations, audits, Supabase records, provider secrets, Alpha boundaries, or client portal behavior.

Certification state: `NEXUS_HERMES_FAILED`
