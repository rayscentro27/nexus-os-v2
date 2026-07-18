# Nexus 3 Capability Legacy Registry Map

Generated: 2026-07-18

| Source | Current Purpose | Runtime Use | Wave 2 Disposition | Future Action |
|---|---|---|---|---|
| `src/lib/capabilities/capabilityRegistry.ts` | Canonical Capability OS output | Executive/Hermes/policy/tests | CANONICAL_SOURCE | Maintain as Wave 2 source of truth |
| `src/hermes/nexus/nexusConnectorRegistry.ts` | Connector definitions, env identifiers, safety flags | Executive health and Capability OS compatibility | COMPATIBILITY_SOURCE | Keep until migrated into capability definitions |
| `src/lib/hermesCapabilityRegistry.ts` | Hermes access map | Hermes/advisor reporting | COMPATIBILITY_SOURCE | Align to Capability OS in later cleanup |
| `src/lib/systemHealthAdapter.ts` | Legacy system health checks | Some legacy UI/report tests | SUPERSEDED | Retire only after consumers are removed |
| `reports/runtime/nexus_repo_intelligence_registry.json` | Repo-intelligence candidates | Executive repo panel and Capability proposals | CANONICAL_SOURCE_FOR_REPO_CANDIDATES | Keep read-only; no installation actions |
| `reports/runtime/nexus_activation_mode_registry.md` | Activation mode report | Report-backed evidence | REPORT_ONLY | Keep as historical evidence |
| `data/operations/nexus_process_registry.json` | Process/runtime status | Dirty runtime evidence | COMPATIBILITY_SOURCE | Treat as stale/read-only unless refreshed by approved run |
| `configs/connector_registry.json` | Legacy connector config | Report/config reference | COMPATIBILITY_SOURCE | Compare before retirement |
| `configs/cli_capability_registry.json` | CLI/tool capability list | Report/config reference | REPORT_ONLY | Do not use for execution authority |
| `configs/nexus_tool_access_registry.json` | Tool access registry | Report/config reference | COMPATIBILITY_SOURCE | Map into future permission registry |
| `configs/specialist_registry.json` | Specialist definitions | Report/config reference | COMPATIBILITY_SOURCE | Keep non-autonomous |
| `configs/stripe_product_registry.json` | Stripe product config | Revenue reference | COMPATIBILITY_SOURCE | Preserve test/live separation |
| `configs/automation_schedule_registry.json` | Automation schedule config | Report-only/manual ops | REPORT_ONLY | Do not start persistent schedulers |

No legacy registry was deleted in Wave 2.
