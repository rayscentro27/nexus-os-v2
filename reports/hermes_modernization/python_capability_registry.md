# Nexus Python Capability Registry

Generated: 2026-08-17

This checkpoint adds the static, deterministic-first Python capability registry for Nexus. It is additive to the existing per-agent runtime capability registry and is meant to answer: "does Nexus already have a deterministic or governed capability for this?"

## Summary

- Registry ID: `NEXUS_PYTHON_CAPABILITY_REGISTRY`
- Version: `1.0`
- Capability count: `27`
- Deterministic: `23`
- API-backed: `3`
- AI-assisted: `1`
- Zero model cost: `23`
- Low external cost: `3`
- Disabled: `1`
- Tenant scoped: `2`
- Client PII classified: `2`

## Capability groups

| Group | Count | Notes |
| --- | ---: | --- |
| Runtime and process reads | 11 | system health, runtime capabilities, process registry, run history, telemetry health |
| Governance reads | 4 | pending approvals, approval status, work order status, work queue |
| Client-scoped reads | 2 | funding readiness, client profile |
| Study reads | 5 | study overview, snapshot, gap summary, business model summary, integration inventory, workflow summary |
| Research intake | 1 | disabled until search keys are available |
| Registry lookup | 1 | capability lookup for the registry itself |
| Operational summary | 1 | read-only operational synthesis |
| Recent runs / telemetry filters | 2 | active runs, recent runs, failed runs, process history, evidence |

## Notes

- Deterministic capabilities remain `ZERO_MODEL_COST`.
- API-backed reads are marked `LOW_EXTERNAL_COST`.
- `get_recent_research` is intentionally disabled and flagged as AI-assisted with approval gating until the search harness is configured.
- The registry is read-only and does not expose shell execution, raw SQL, or arbitrary filesystem mutation.

## Representative capability metadata

- `get_system_health` - deterministic read, zero model cost, system scope.
- `get_process_registry_live` - deterministic process registry read, zero model cost.
- `get_runtime_execution_summary` - verified runtime telemetry read, zero model cost.
- `get_funding_readiness` - API-backed, tenant-scoped client read, low external cost.
- `get_client_profile` - API-backed, tenant-scoped client read, low external cost.
- `get_recent_research` - disabled AI-assisted research intake placeholder, AI tier 1.
- `get_python_capability_registry` - registry lookup capability for deterministic capability discovery.

