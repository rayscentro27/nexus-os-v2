# Nexus Hermes Plugin

## Scope

- Bundled upstream-Hermes plugin path: `plugins/nexus-hermes-plugin/`
- Manifest: `plugin.yaml`
- Entry point: `register(ctx)`
- Boundary: read-only, governed, deterministic-first

## Registered Tools

1. `nexus_capability_lookup`
2. `nexus_system_status`
3. `nexus_process_status`
4. `nexus_runtime_status`
5. `nexus_research_status`
6. `nexus_marketing_status`
7. `nexus_revenue_status`
8. `nexus_pending_approvals`
9. `nexus_automation_health`
10. `nexus_client_summary`
11. `nexus_credit_summary`
12. `nexus_business_foundation_summary`
13. `nexus_funding_readiness_summary`

## Deterministic Routing

- Capability lookup uses the static Python capability registry.
- Read-only status tools route through existing governed shared readers.
- No shell, SQL, filesystem mutation, or generic write tool is registered.

## Governance

- Client-scoped tools require `email` or `client_id`.
- PII boundaries remain explicit in the backing shared capabilities.
- Read-only default is preserved for every tool.

## Verification

- Plugin registration tests: passing
- Hermes discovery test: passing
- Deterministic lookup test: passing
- Read-only boundary test: passing

