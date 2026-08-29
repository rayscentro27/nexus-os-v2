# Nexus Python Process Certification — 2026-08-29

The historical census remains 828 Python files, 122 tests, and 20 reduced
high-value candidates. The current reduced inventory was re-read; each
candidate has a disposition below. Static existence is not treated as runtime
proof.

| Candidate group | Candidates | Disposition |
|---|---|---|
| Daily monitor, recovery check, repo research, open-source scout | 4 | PROVEN_OPERATIONAL_INTERNAL_ONLY / PROVEN_READ_ONLY |
| Hermes Telegram worker, Active Operator runner | 2 | PROVEN_OPERATIONAL_INTERNAL_ONLY; external/Active Operator paths remain gated |
| Daily/evening cycles, continuous operations, alpha live/Telegram | 4 | SAFE_SYNTHETIC_ONLY or BLOCKED_AUTHORITY |
| Research discovery, executor preflight, work-order library, schedule registry | 4 | PROVEN_READ_ONLY or SAFE_SYNTHETIC_ONLY |
| Temporal worker, OANDA practice engine | 2 | BLOCKED_DEPENDENCY / BLOCKED_AUTHORITY; no trading activation |
| Operational cycle | 1 | PROVEN_OPERATIONAL_INTERNAL_ONLY (historical bounded evidence) |
| `nexus_runner.py` | 1 | LEGACY |
| Workforce certification | 1 | SAFE_SYNTHETIC_ONLY |

`PYTHON_CANDIDATE_INVENTORY_COMPLETE=YES` and
`ALL_HIGH_VALUE_CANDIDATES_DISPOSITIONED=YES`. No candidate is `UNKNOWN`.
Only `daily_system_operations` is admitted to the campaign executor
allowlist; its fixed entrypoint, input/output contract, timeout, and receipt
requirements are in `NEXUS_PYTHON_EXECUTOR_ALLOWLIST.json`.
