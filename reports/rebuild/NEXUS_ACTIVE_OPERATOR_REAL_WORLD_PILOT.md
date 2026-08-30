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

The first request exposed a lifecycle defect: successful execution wrote only
the cycle receipt and left the item `READY`, causing two scheduled executions.
Both receipts remain preserved. The item is now reconciled from that evidence
as historical `COMPLETE` with `attempt_count=2`; this reconciliation is not
counted as fresh certification.

The repaired lifecycle persists claim, running, completion, validation, hash,
receipt, execution, and idempotency fields. A new non-synthetic request,
`wp6-openai-updates-official-20260830-01`, is queued for official OpenAI-owned
source research and has not been invoked or completed manually.

## Post-repair certification

The repaired fresh item `wp6-openai-updates-official-20260830-01` was selected
by launchd at 15:20:35 UTC, executed once through the Research Alpha route,
validated with 19 live SearXNG results, and persisted as `COMPLETE`. The next
launchd cycle at 15:35:38 UTC produced `NO_ACTION` and did not select it again.
This proves exactly-once work-item execution and next-cycle exclusion for the
fresh item.

Live web acquisition is proven. Primary-source page retrieval and primary-source
verification are not proven: the adapter consumes search-result snippets,
including third-party aggregators, even when an OpenAI-owned URL appears.

## Limits

- The scheduler was not manually triggered.
- VM reboot recovery and sustained long-duration operation remain unproven.
