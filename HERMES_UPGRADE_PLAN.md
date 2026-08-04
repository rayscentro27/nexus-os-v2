# Hermes Upgrade Plan

Generated: 2026-08-03

## Dependency Decisions

| Dependency | Previous | Installed | Decision |
| --- | ---: | ---: | --- |
| `@supabase/supabase-js` | `^2.45.0` | `^2.112.0` | Upgrade; browser client remains anon-key only with session persistence enabled. |
| `lucide-react` | `^0.460.0` | `^1.28.0` | Upgrade; `Youtube` export replaced by `Video as Youtube` compatibility alias. |
| `vitest` | `^4.1.9` | `^4.1.10` | Patch upgrade; full non-e2e suite passes. |
| `vite` | `^5.4.2` | unchanged | Not upgraded; audit fix requires Vite 8 via force and is a breaking major. |

## Architecture Upgrade

- Added `src/lib/nexusOperationalTruth.ts`.
- Added explicit Hermes operational intelligence version: `Hermes Operational Intelligence v2.1`.
- Added process registry schema version: `nexus-process-registry-v1`.
- Added bounded browser probes for Supabase and Hermes model gateway.
- Added operational question answers that do not fall back to generic process descriptions.

## Process Registry Upgrade

- Added migration `20260803120000_authoritative_process_run_registry.sql`.
- Added admin-only tables for process definitions, process runs, provider probes, research runs, and normalized research results.
- Added local append-only spool adapter at `scripts/operations/process_registry_adapter.py`.
- Changed `nexus_active_operator_runner.py` so receipt-only work is recorded as `SIMULATED`, not completed success.

## Clyde and Upload Upgrade

- Client-facing advisor labels now say Clyde.
- Internal Nexus Hermes and Hermes Alpha names were preserved.
- Inline uploads are upload-first; category confirmation appears only after a low-confidence classification.
- Upload metadata now records classification state, confidence, and basis.
