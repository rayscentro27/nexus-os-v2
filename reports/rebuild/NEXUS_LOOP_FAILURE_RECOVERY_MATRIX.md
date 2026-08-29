# WP4 Loop Failure / Recovery Matrix — 2026-08-29

The reusable kernel fails closed and emits a receipt for every attempted run.

| Failure | Kernel behavior | Evidence |
|---|---|---|
| missing skill or loop | `NO_SKILL_MATCH` / `NO_LOOP_MATCH` | resolver and loop tests |
| authority mismatch | `SKILL_BLOCKED_AUTHORITY` | resolver test |
| executor mismatch/failure | `SKILL_EXECUTOR_NOT_ALLOWED` or `FAILED` | kernel tests |
| malformed or non-PASS result | `FAILED`, `NOT_PROVEN` validation | kernel test |
| stale/unsafe context | rejected before executor | `_assert_context` |
| private SearXNG adapter quoting defect | failed receipt, then corrected bounded retry | `receipt_a137afb90b764cf8993d9052552ad7c7.json`, `receipt_32d0bf9f29b74b94930cda987dddd7f4.json` |
| review failure | `review_not_verified`, no success state | kernel contract |

No failure path invents success, invokes arbitrary shell, writes TruthKernel
authority, or performs external action. Retry remains bounded by each loop's
declared policy.
