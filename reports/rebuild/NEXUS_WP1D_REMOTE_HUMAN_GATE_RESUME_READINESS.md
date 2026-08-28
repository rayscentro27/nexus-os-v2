# WP1-D Remote Human Gate / Resume Readiness

## Readiness result

`PREPARED_NOT_ACTIVATED`

The existing Telegram path can be reused as a transport and identity boundary,
but it is not yet a TruthKernel-backed remote rebuild gate. No new authority
was activated and no Telegram message was sent.

## Existing path audit

| Requirement | Current evidence | Result |
|---|---|---|
| Telegram approval route | `scripts/nexus_agent_platform/human_gate_router.py`, invoked by the Hermes worker | REUSE POSSIBLE |
| Authorized identity | Hermes worker rejects chats not in the configured allowlist before routing | EXISTING BOUNDARY |
| Exact gate binding | Existing `gate_id` lookup and expected response comparison | PARTIAL |
| Exact requested action | Existing gate `expected_response`; no TruthKernel `exact_action` integration | NOT INTEGRATED |
| Expiry | TruthKernel enforces expiry; existing JSON gate router does not | KERNEL READY / ROUTE GAP |
| Replay protection | Closed gate returns `ALREADY_CLOSED`; TruthKernel approval is one-way | PARTIAL |
| HOLD safety | Existing manual HOLD is command-scoped; generic router expects configured response | PARTIAL |
| Durable receipt | Existing resume receipt and gate ledger; no TruthKernel approval receipt bridge | PARTIAL |

Receipt locations are the existing human-gate ledger and Telegram operator
receipt directories. Exact token values and credential locations are excluded.

## Future flow boundary

The safe implementation should wrap the existing route with a TruthKernel
adapter that validates authorized chat, exact `gate_id`, exact `exact_action`,
expiry, and one-time status before writing an approval receipt. Activation
would change the approval security boundary and therefore requires a specific
human gate; it is not part of this readiness package.

`REMOTE_GATE_APPROVAL_SUPPORTED=PARTIAL`.
`CODEX_SESSION_CAN_AUTO_RESUME_WHILE_ALIVE=NO evidence found`.
`CODEX_SESSION_CAN_RESTART_AFTER_TERMINATION=NO existing supervised engineering harness found`.
`REMOTE_APPROVAL_READY=NO`.
`REMOTE_RESUME_READY=NO`.
`ACTIVATION_CHANGE_REQUIRED=YES`.
`HUMAN_AUTHORITY_REQUIRED=YES for activation`.
