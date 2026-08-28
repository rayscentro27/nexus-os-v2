# WP1-D Activation Result

`CODE_INTEGRATION_COMPLETE_SERVICE_E2E_BLOCKED`

The existing Hermes Telegram human-gate route now delegates exact
`APPROVE <gate_id>` / `HOLD <gate_id>` responses to TruthKernel when invoked
with the authorized chat allowlist. TruthKernel enforces exact action,
expiry, one-time approval, and durable gate events. Approval scope is the
recorded exact action only.

Adversarial tests cover authorized and unauthorized chats, unknown and wrong
gates, wrong actions, expiry, replay, HOLD, and malformed input. No live
campaign or production state was changed by these tests.

The worker source path is connected, but real Telegram delivery/correlation
was not attempted because `com.nexus.telegram-hermes-v2` is not loaded. A
real E2E test would require a separate explicit service-state authorization to
start/load/change supervision of that worker. This approval did not include
that action.

`TRUTHKERNEL_CONNECTED=YES`
`TELEGRAM_ROUTE_CONNECTED=YES`
`REAL_TELEGRAM_E2E=NO`
`SERVICE_STATE_CHANGE_REQUIRED=YES`

## Real Telegram E2E verification

The approved temporary gate was verified from persisted artifacts:

- `REAL_TELEGRAM_OUTBOUND=YES`; gate notification message ID `721`.
- `REAL_TELEGRAM_INBOUND=YES`; worker receipt update ID `197233445`.
- `AUTHORIZED_IDENTITY_ENFORCED=YES`; stored actor hash matches the approved
  allowlisted Telegram identity.
- `GATE_ID_MATCH=YES`; `HG-REMOTE-E2E-20260828-01`.
- `EXACT_ACTION_MATCH=YES`; `APPROVE HG-REMOTE-E2E-20260828-01`.
- TruthKernel gate status is `APPROVED`; approver and approval timestamp are
  persisted.
- Telegram operator receipt is delivered with response message ID `723`.
- TruthKernel gate event `gate_event_3b6c90abc1e44010b5e8ad2b72767fb6` is
  persisted.
- Deterministic replay returned `DENIED_REPLAY_OR_CLOSED`; the gate remained
  `APPROVED` and authority scope did not broaden.

`WP1-D-TELEGRAM-E2E=COMPLETED`.
`REMOTE_APPROVAL_READY=YES`.
`CONTINUOUS_RUNTIME_PROVEN=NO`; the worker is launchd-supervised `--once`,
not a sustained continuous process proof.
