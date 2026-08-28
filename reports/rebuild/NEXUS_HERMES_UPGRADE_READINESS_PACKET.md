# Hermes Upgrade Readiness Packet

## Status

`READY_FOR_EXPLICIT_AUTHORIZATION — NOT REQUESTED IN THIS CHECKPOINT`

This packet is preparatory only. No Hermes runtime was upgraded, installed,
reconfigured, or restarted.

| Item | Current truth |
|---|---|
| CURRENT VERSION | Local version was not confirmed by bounded audit; installed Hermes source/binary identity remains `UNKNOWN` |
| TARGET VERSION | A specific target must be selected after Ray authorizes the upgrade scope |
| NATIVE FEATURES TO BE USED | Bot Mode, persistent sessions/memory, skills, MCP, browser/tools, routines, provider routing, retries, messaging gateways, delegation where compatible |
| NEXUS FEATURES TO BE REPLACED/WRAPPED | Python authority, deterministic process execution, approvals, evidence, receipts, verification, and safety policy remain Nexus-owned; Hermes is wrapped at the interface |
| BACKUP/ROLLBACK PLAN | Preserve current profile/config and launchd declarations; snapshot before change; restore prior runtime/config and verify Telegram one-shot behavior |
| EXPECTED CONFIG CHANGES | Explicitly enumerated only after target/version and approved scope are selected |
| SECURITY BOUNDARY | No credential rotation; no expansion of external-action, payment, trading, deployment, or client-mutation authority |
| TRUTH-KERNEL INTEGRATION | Hermes consumes read-only structured process status; it cannot assert verification or mutate evidence |
| COMMUNICATION IMPROVEMENT PLAN | Re-run deterministic communication benchmark and real harmless status/control checks after authorized change |
| TEST PLAN | Static/config audit, focused Python tests, launchd dry inspection, bounded one-shot checks, Telegram receipt/correlation review, rollback validation |

## Gate boundary

The actual upgrade requires a dedicated human gate bound to the exact target,
scope, and rollback plan. The existing Telegram approval route provides an
authorized-chat boundary and one-time closed-gate behavior, but its current
JSON router is not yet integrated with TruthKernel `exact_action` and expiry
semantics. It must be wrapped and separately activated before it can be the
remote upgrade authority.

`HUMAN_AUTHORITY_REQUIRED=YES`.
`UPGRADE_EXECUTED=NO`.
