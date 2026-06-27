# Nexus AI Department Access Control

Separates the AI agents so each has a distinct, least-privilege capability profile. Source of truth:
`src/config/nexusAIDepartmentRoles.ts`, `src/config/nexusAIAgentAccessPolicy.ts`,
`src/config/nexusClientDataSensitivityPolicy.ts`, enforcement in `src/lib/nexusAIAccessPolicy.ts`.

Core principle: Nexus can work internally; it cannot leave the building without approval.

## Roles

| Role | Internet | Vault adapter | Approved-knowledge-only | Raw client data | Client-facing output |
|---|---|---|---|---|---|
| Hermes (CEO/Advisor) | yes | no | no | **no** | approval-gated |
| Researcher AI | yes | no | no | **no** | blocked |
| Credit Specialist AI | **no** | yes (mock v1) | yes | only via adapter | approval-gated |
| Funding Specialist AI | **no** | yes (mock v1) | yes | only via adapter | approval-gated |
| Business Setup Specialist AI | **no** | yes (mock v1) | yes | only via adapter | approval-gated |
| Client Chat AI | **no** | yes (own-client) | yes | only via adapter | approval-gated |

## Invariants (enforced by `verifyAccessInvariants()`)

1. Hermes cannot access any raw/private client data category.
2. Internet-enabled roles must NOT also have Client Vault access (hard separation).
3. Credit/Funding/Business specialists have no web tools (Supabase-only).
4. Researcher AI cannot access client PII.
5. Every role's client-facing output is blocked or approval-gated — never auto-emitted.
6. Specialists + Client Chat must use approved knowledge only.

Verify: `python3 scripts/ai_access/verify_ai_department_access.py --dry-run --json`.

## Runtime enforcement

These invariants are enforced at call time by the [Nexus AI Agent Runtime](NEXUS_AGENT_RUNTIME.md)
(`src/lib/nexusAgentRuntime.ts`): agents read the Client Vault only through the runtime, which gates
every read on `canUseTool` + `canAccessData` + own-client scoping and records a `ClientAuditEvent`
(allowed or denied). Verify: `python3 scripts/ai_access/verify_agent_runtime.py --dry-run --json`.
