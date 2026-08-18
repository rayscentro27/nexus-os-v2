# Worker Redundancy Benchmark — Phase 13B

## Current result

Secondary AI worker: `NOT_AVAILABLE`.

| Worker | Current status | Evidence | Decision |
|---|---|---|---|
| Codex | `AVAILABLE` | current verified harmless execution checkpoint | primary health-positive worker |
| MiMo | `INSTALLED_UNPROVEN` | provider-specific `mimo run --non-interactive` contract exists, but prior execution did not prove success | do not select |
| Kilo | `INSTALLED_UNPROVEN` | version `7.3.54`; no safe headless execution command proven from local CLI/config | defer and do not register |
| OpenCode | `UNAVAILABLE` | `opencode run --format json` bounded probe timed out | do not increase timeout blindly |
| Local worker | `AVAILABLE` | isolated deterministic artifact + verification | compatible fallback |

The current builder registry intentionally keeps health-positive external CLIs separate from executable adapters. Therefore the safe route is:

```text
certified primary unavailable
  → next compatible certified execute adapter, if one exists
  → local deterministic worker for compatible deterministic tasks
  → otherwise blocked; verification cannot be bypassed
```

The fallback policy is covered by the existing builder abstraction tests. Production default routing was not changed.
