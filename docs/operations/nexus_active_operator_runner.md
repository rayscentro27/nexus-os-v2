# Nexus Active Operator Runner — Documentation

**Generated**: 2026-07-05

---

## Usage

```bash
# Run all enabled processes once
python3 scripts/operations/nexus_active_operator_runner.py --once

# Dry run (simulate only)
python3 scripts/operations/nexus_active_operator_runner.py --dry-run

# Run specific category
python3 scripts/operations/nexus_active_operator_runner.py --category daily_monitor

# Telegram-triggered run (extra safety checks)
python3 scripts/operations/nexus_active_operator_runner.py --telegram-triggered
```

## Safety

- Only runs processes with mode: ACTIVE_INTERNAL, DRY_RUN, or SANDBOX_TEST
- Skips BLOCKED processes
- Telegram-triggered runs skip high-risk processes
- Writes receipts for every run
- Updates heartbeat
- Never runs forever (use --once)
- Never executes blocked external actions

## Output

- `reports/runtime/nexus_active_operator_heartbeat_latest.json`
- `reports/runtime/nexus_active_operator_runner_latest.md`
- `reports/runtime/nexus_active_operator_receipts/` (per-run receipts)

## Business Active Operator extension

The hourly `com.nexus.active-operator-v2` dispatch also reads the canonical
GoClear Opportunity Engine, Revenue Truth Hub, Growth Operations, and existing
governance state. It produces compact `nexus.business-attention.v1` findings
under `nexus.business-priority.v1`, preserving P0 system findings above
business priorities.

Business work reuses existing approvals and work orders. The only autonomous
business action is a bounded internal priority brief at
`reports/runtime/nexus_active_operator_business_brief_latest.md`. Publishing,
messaging, financial mutation, funding submission, trading, production DB
mutation, and arbitrary shell remain unavailable.

Business state is deduplicated by stable source keys plus material fingerprints;
unchanged hourly state does not create new work. The heartbeat and receipt
include source status, business findings, priorities, safe actions, work-order
counts, and duplicate suppression without client PII.
