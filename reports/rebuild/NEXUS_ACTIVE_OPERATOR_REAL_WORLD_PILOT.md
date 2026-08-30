# WP6 Active Operator bounded real-world pilot

## Current state

Campaign gate: `HG-WP6-ACTIVE-OPERATOR-BOUNDED-REAL-WORLD-PILOT-20260830-01`

TruthKernel status: `APPROVED`; durable approval event recorded.

Mode: `BOUNDED_INTERNAL_ONLY`; deterministic switch enabled.

Canonical scheduler: `com.nexus.active-operator-v2` via launchd.
Current interval: 900 seconds (15-minute bounded stability phase).
No payments, trades, client-production mutations, unapproved external
messages, or deployments were performed.

## Audited implementation

- Canonical runner: `scripts/operations/nexus_active_operator_runner.py`
- Canonical launchd definition: `ops/launchd/com.nexus.active-operator-v2.plist`
- Existing mode: bounded one-shot launchd invocation, currently not loaded
- Existing lock: `data/runtime/nexus_active_operator.lock`
- Existing receipts: `reports/runtime/nexus_active_operator_receipts/`
- Existing heartbeat: `reports/runtime/nexus_active_operator_heartbeat_latest.json`
- Existing safety profile blocks payments, live trading, client production
  mutation, external outreach, arbitrary shell, and authority self-modification.

## Real scheduled evidence

Six OS-scheduled cycles were observed between 14:09:32 and 14:34:39 UTC on
2026-08-30. All six had `NEXUS_OPERATOR_TRIGGER=launchd`, no dry-run flag,
exit code 0, durable runtime receipts, and no external mutations. All six
were `NO_ACTION` cycles. No Codex or manual cycle trigger was used.

The six receipts are retained under
`reports/runtime/nexus_active_operator_receipts/` and are the authoritative
cycle evidence. The post-threshold scheduler reload reset launchd's in-memory
run counter; durable receipts preserve the six-cycle proof.

## Research amendment

Exactly one non-synthetic public research request was added to the governed
Alpha research queue. It has not been manually invoked or marked complete.
The bounded runner now reads this queue and may select it only on a future
OS-scheduled cycle.

## Limits

- A real action cycle is not yet proven; no eligible item was selected during
  the six-cycle 5-minute threshold window.
- The next stability cycle is intentionally not manually triggered.
- VM reboot recovery and sustained long-duration operation remain unproven.
