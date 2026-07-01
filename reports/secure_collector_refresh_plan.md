# Secure Collector Refresh Plan

**Generated:** 2026-07-01

## Principle

Do not add arbitrary shell execution to the frontend. If secure refresh is not already safely available, create the plan and/or copy-command card only.

## Current Collectors

| Collector | Path | Status | Safe |
|-----------|------|--------|------|
| Operations Status | scripts/ops/collect_nexus_operations_status.py | available | Yes |
| Second Brain Index | scripts/ops/build_hermes_second_brain_index.py | available | Yes |
| Model Infrastructure | scripts/ops/collect_hermes_model_infrastructure.py | available | Yes |

## Frontend Refresh

- **Available:** No
- **Reason:** No secure shell execution endpoint exists in frontend
- **Recommendation:** Create a copy-command card that shows the command to run, but do not execute from frontend

## Background Job Refresh

- **Available:** Yes
- **Schedulers:** com.nexus.daily-operating, com.nexus.evening-closeout, com.nexus.continuous-ops-daily
- **Note:** Background jobs can run collectors safely via launchd. No frontend shell execution needed.

## Copy Commands

```bash
# Operations Status
python3 scripts/ops/collect_nexus_operations_status.py

# Second Brain Index
python3 scripts/ops/build_hermes_second_brain_index.py

# Model Infrastructure
python3 scripts/ops/collect_hermes_model_infrastructure.py

# All collectors
python3 scripts/ops/collect_nexus_operations_status.py && python3 scripts/ops/build_hermes_second_brain_index.py && python3 scripts/ops/collect_hermes_model_infrastructure.py
```

## Security Notes

- No arbitrary shell execution from frontend
- Collectors are read-only scripts
- All output goes to reports/ directory
- No secrets exposed in commands
