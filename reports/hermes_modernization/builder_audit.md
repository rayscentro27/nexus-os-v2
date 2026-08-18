# Builder Audit

## Existing surfaces

| Component | Classification | Reason |
|---|---|---|
| scripts/runner_handlers/_base.py | WRAP | Generic subprocess runner already supports bounded script execution. |
| scripts/client_flow/common.py | MERGE | Local-only builder/report helpers already write structured outputs. |
| scripts/client_flow/run_client_portal_backend_build.py | DEFER | Client portal build flow is protected and not part of this phase. |
| scripts/creative/lab.py | WRAP | Creative Lab already produces an approved build spec and pilot artifact. |
| scripts/creative/run_creative_lab.py | WRAP | Existing Creative Lab report driver can seed the safe builder proof. |
| scripts/nexus_agent_platform/runtime/execution_telemetry.py | EXTEND | Verified execution telemetry already records actual runtime boundaries. |
| scripts/nexus_agent_platform/loops/runtime.py | EXTEND | Loop runtime already enforces bounded retries and cost control patterns. |
| scripts/nexus_agent_platform/hermes_lab/upstream_compatibility.py | MERGE | Upstream lab sandboxing and subprocess probes are reusable here. |
| src/lib/nexusSectionStatusRegistry.ts | WRAP | CLI/tool availability inventory already exists and informs routing. |
| reports/cli_tool_registry_latest.json | WRAP | Read-only tool registry evidence already captures installed vs authorized state. |
| scripts/runner_handlers/design_handlers.py | MERGE | Deterministic script delegation pattern can be reused for builder orchestration. |
| scripts/hermes/create_manual_model_packet.py | WRAP | Manual packet pattern is useful for future worker handoffs, not execution. |
| OpenHands integration | DEFER | Not installed or proven on this machine. |
| provider-neutral CodingWorker contract | CREATE_NEW | This phase introduces the missing builder abstraction. |
