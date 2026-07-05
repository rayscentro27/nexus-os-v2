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
