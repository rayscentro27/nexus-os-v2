# WP6 Active Operator bounded real-world pilot

## State

Campaign gate: `HG-WP6-ACTIVE-OPERATOR-BOUNDED-REAL-WORLD-PILOT-20260830-01`

Gate status: `PENDING`

Active Operator status: `PAUSED`

No scheduler activation, cycle start, host service change, or autonomous work
was performed during preparation.

## Audited implementation

- Canonical runner: `scripts/operations/nexus_active_operator_runner.py`
- Canonical launchd definition: `ops/launchd/com.nexus.active-operator-v2.plist`
- Existing mode: bounded one-shot launchd invocation, currently not loaded
- Existing lock: `data/runtime/nexus_active_operator.lock`
- Existing receipts: `reports/runtime/nexus_active_operator_receipts/`
- Existing heartbeat: `reports/runtime/nexus_active_operator_heartbeat_latest.json`
- Existing safety profile blocks payments, live trading, client production
  mutation, external outreach, arbitrary shell, and authority self-modification.

## Proposed bounded pilot contract

The pending campaign authorizes only a five-minute OS schedule for bounded
internal work, one concurrent cycle, a ten-minute cycle limit, at most three
work items, at most one heavy research task, deterministic kill-switch and
singleton checks, durable cycle receipts, and internal reporting when needed.
External consequential actions remain zero-authorized. Active Operator must
remain paused until the exact TruthKernel gate is approved.

## Real-world evidence

No real scheduled cycles exist yet. Unit, manual, dry-run, and synthetic
evidence will not count toward the six-cycle certification requirement.
