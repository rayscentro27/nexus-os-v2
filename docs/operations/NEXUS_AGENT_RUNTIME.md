# Nexus AI Agent Runtime

The runtime that turns the static AI access contracts into **runtime-enforced** behavior with an
audit trail. Every Specialist/agent reads the Client Vault ONLY through this runtime.

Source: `src/lib/nexusAgentRuntime.ts`. Python mirror + verification:
`scripts/ai_access/agent_runtime_model.py`, `verify_agent_runtime.py`, `generate_agent_runtime_report.py`.

## What it enforces (at call time)

For every wrapped vault read, the runtime guard runs in order and **fails closed**:

1. `canUseTool(role, tool)` — e.g. internet roles have no `client_vault_adapter` tool.
2. `canAccessData(role, dataCategory)` — private categories are vault-only; Hermes/Researcher denied.
3. Own-client scoping — `client_chat_ai` may read only its `allowedClientId`; other clients denied.
4. Audit — a `ClientAuditEvent` (allowed OR denied) is recorded to the `AuditSink` and the vault
   adapter. Denied reads return `{ allowed: false, data: null }`.

## Wrapped methods

`listClientProfiles, getCreditReport, getCreditScoreSnapshots, getBusinessProfile,
listBusinessSetupItems, listProofUploads, listLetterPackets, listMailingRecords, listWorkflowTasks,
listReminderTasks, getFundingReadiness, listAffiliateAttribution, listConsentEvents,
exportSanitizedSignals` (the last is the only path that may feed Hermes).

## Usage

```ts
import { createAgentRuntime, AuditSink } from '../lib/nexusAgentRuntime';

const sink = new AuditSink();
const specialist = createAgentRuntime({ role: 'credit_specialist_ai', actorId: 'credit_specialist', sink });
const res = await specialist.getCreditReport('dev-c1'); // allowed → res.data, res.audit
const hermes = createAgentRuntime({ role: 'hermes_ceo_advisor', actorId: 'hermes', sink });
const blocked = await hermes.getCreditReport('dev-c1'); // denied → blocked.data === null, audited
```

## Verification

`python3 scripts/ai_access/verify_agent_runtime.py --dry-run --json` proves: Hermes + Researcher are
denied on every private read; specialists are allowed via the adapter; Client Chat is own-client
scoped; sanitized export is allowed for Hermes but denied for Researcher; and **every** call (allowed
or denied) produces exactly one audit event. Mock adapter only — no live vault, no second Supabase.

This is the prerequisite for later flipping a `LiveClientVaultAdapter` on safely (see
[NEXUS_CLIENT_VAULT_LATER_CONNECTION_PLAN.md](NEXUS_CLIENT_VAULT_LATER_CONNECTION_PLAN.md)).
