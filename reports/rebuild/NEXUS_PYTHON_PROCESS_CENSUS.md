# Nexus V2 Python Process Census — Sprint 0 WP0-B

## Scope and evidence

This is a static census plus bounded, non-mutating inspection. It is not an
operational certification. A Python file, registry row, test, or receipt is
not treated as proof that a process works.

- Repository checkpoint inspected: `4c861372aa5b6553344ff15c020d444d48d984bb`
- Python files under `scripts/`: **828**
- Python test files: **122**
- Launchd plist files inspected as scheduler declarations: **66**
- `python3 -m compileall -q scripts`: **PASS** (static compilation only)
- Bounded help probes: not completed because the macOS environment lacks the
  `timeout` utility used to bound long-running entrypoints; no process was
  launched without a bound.
- External mutations, service restarts, credential changes, and production
  actions: **none**

## Representative classification map

| Classification | Representative paths | Evidence status |
|---|---|---|
| CANONICAL_EXECUTOR candidate | `scripts/operations/nexus_active_operator_runner.py`, `scripts/operations/nexus_hermes_telegram_worker.py` | Source exists; runtime purpose must be proven per process |
| SUPPORT_LIBRARY | `scripts/nexus_agent_platform/capabilities/`, `scripts/operations/process_registry_adapter.py` | Imported/support code; not independently operational |
| AGENT | `scripts/alpha/`, `scripts/hermes/`, `scripts/voice/` | Components exist; connection and side effects vary |
| ORCHESTRATOR | `scripts/run_nexus_continuous_operations.py`, `scripts/operations/` orchestration paths | Scheduler/orchestration declarations; execution not inferred |
| CONNECTOR | `scripts/nexus_agent_platform/connectors/`, capability clients | Provider-specific; credentials and live responses require proof |
| MONITOR | `scripts/operations/nexus_daily_monitor.py`, `scripts/operations/nexus_recovery_check.py` | Safe read/report candidates; no certification from source alone |
| SCHEDULER | launchd wrappers and continuous-operation launchers | Loaded/configured is distinct from running and completing |
| DATA_PROCESSOR | research, credit, client, and report-generation scripts | Inputs and freshness require per-process review |
| TEST | 122 Python test files | Test evidence is isolated from live operational evidence |
| LEGACY / DUPLICATE / STUB / UNKNOWN | Multiple similarly named scripts and historical paths | Requires package-level disposition before reuse |

## Known entrypoint risk

The registry commonly points at generic Active Operator machinery. That path
must not be interpreted as an implementation of every named process. Each
candidate requires source-level dispatch inspection, input/output tracing, and
purpose-appropriate runtime evidence.

## Safe-canary ledger

Two bounded internal/read-only canaries were run through their no-argument
entrypoints with a five-second subprocess bound:

- `scripts/operations/nexus_daily_monitor.py`: **PROVEN_WORKING_PARTIAL** for
  diagnostic report generation. It produced a fresh runtime summary, but its
  report also surfaced stale/missing telemetry, so this is not a health
  certification.
- `scripts/alpha/alpha_open_source_scout.py`: **PROVEN_WORKING_PARTIAL** for
  candidate discovery. It returned `ok=true`, selected a candidate, and
  reported zero AI executions. This proves bounded local discovery only, not
  live Alpha business operation.

No external mutation, worker restart, credential change, or campaign evidence
was produced. The census remains **IN_PROGRESS**: static inventory and two
canaries are recorded, while full runtime classification and call-graph
evidence remain open.

## Required continuation

Build a generated candidate table from executable entrypoints, inspect their
dispatch and side-effect boundaries, then run only individually bounded
read-only/internal-safe canaries. Record command, inputs, output, validation,
and receipt for each canary.

The reduced canonical inventory is recorded in
`reports/rebuild/NEXUS_PYTHON_EXECUTABLE_CANDIDATES.json`: 20 high-value
executable candidates were selected from the 828-file census. It separates
`RUN_ONCE`, `ON_DEMAND`, `SCHEDULED`, and `CONTINUOUS`, and records sustained
execution separately from launchd configuration.

The reduced canonical inventory is recorded in
`reports/rebuild/NEXUS_PYTHON_EXECUTABLE_CANDIDATES.json`: 20 high-value
executable candidates were selected from the 828-file census. It separates
`RUN_ONCE`, `ON_DEMAND`, `SCHEDULED`, and `CONTINUOUS`, and records sustained
execution separately from launchd configuration.
