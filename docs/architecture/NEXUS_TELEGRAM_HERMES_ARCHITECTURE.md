# Nexus Telegram / Hermes Architecture

Telegram is a communication surface. Authenticated updates enter the existing
Nexus worker, while `APPROVE` and `HOLD` gate messages continue through the
dedicated TruthKernel human-gate router before ordinary operator routing.

Telegram uses three explicit lanes. Conversation goes to a bounded Hermes
response, state queries read canonical Nexus state without launching work, and
only execution requests use the full governed chain. Safe execution intents
resolve through the department, loop, skill, worker, and capability registries.
Unknown intents produce clarification and no execution.

The lane contract is `CONVERSATIONAL_LANE`, `READ_ONLY_STATE_LANE`, or
`EXECUTION_LANE`; `UNKNOWN` always returns clarification without execution.
The Oracle Hermes bridge remains private and advisory; no public Hermes
endpoint, unrestricted tool path, or TruthKernel mutation is granted.

The former router remains in place as rollback compatibility until WP5 real
Telegram certification proves the new route.

Execution responses follow `execute → verify → extract → summarize → explain →
next action`; internal receipt paths remain evidence rather than the answer.
