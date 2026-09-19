# NEXUS Hermes/Nova Research↔Alpha Evidence Bridge Certification

HERMES_READ_PATH=Hermes 0.20.6 / profile=nova_nexus / nexus_mcp_remote → Nexus MCP HTTP reverse tunnel → nexus_get_research_state(objective_id) and nexus_get_alpha_review(objective_id) → research_evidence_bridge.resolve_objective → objective-lineage latest reducer → Nova response.
NEXUS_MCP_RESEARCH_TOOL=nexus_get_research_state(objective_id)
NEXUS_MCP_ALPHA_TOOL=nexus_get_alpha_review(objective_id)

FAILURE_REPRODUCED=YES; prior fresh objective answers selected global argument-less operational state and stale CRJ/affiliate records; Alpha was not joined to the fresh objective lineage.
STALE_DATA_ROOT_CAUSE=Research and Alpha MCP reads had no objective_id arguments, the global latest reducer was used, and Hermes could omit the new argument; stale historical state therefore remained eligible.

OBJECTIVE_FIRST_RESOLUTION=YES
SOURCE_AUTHORITY_MATRIX=objective/work ledger → objective-linked persisted Research package → objective/investigation-linked Alpha evaluation and receipt → same-chain follow-up; historical summaries are context only and cannot override current lineage.
PARENT_CHAIN_RESOLUTION=YES; objective_id → investigation_id/work linkage → research_package_id → Alpha evaluation/receipt → follow-up work ID is persisted and resolved by exact identifiers.
OBJECTIVE_SCOPED_LATEST_STATE=YES; latest valid record is reduced only within the requested objective lineage.
HISTORICAL_CONTAMINATION_GUARD=YES; unresolved or missing objective lineage returns explicit missing evidence rather than unrelated records.

MCP_OBJECTIVE_LOOKUP=PASS_REAL via objective-scoped Research/Alpha canonical reads; objective is returned exactly.
MCP_RESEARCH_LOOKUP=PASS_REAL; package_4fffe7519d18ead82fdc returned for the fresh objective.
MCP_ALPHA_LOOKUP=PASS_REAL; alpha_receipt_002338565d8c4a76a9772539914b0d9b and RESEARCH_MORE returned for the same objective.
MCP_PARENT_CHAIN=PASS_REAL; objective, package, Alpha receipt, and follow-up work ID matched.

HERMES_RESEARCH_GROUNDING_CONTRACT=RESOLVED_OBJECTIVE_ID + LATEST_RESEARCH_PACKAGE + LATEST_ALPHA_RECEIPT + MISSING_EVIDENCE + CURRENT_NEXT_ACTION are required; unavailable fields are reported explicitly. A bounded transport projection from canonical records prevents a remote model turn that omits objective arguments from falling back to global history.

NEW_HERMES_OBJECTIVE_ID=hermes-bridge-cert-appointment-reminder-segment-v2-20260919
NEW_RESEARCH_PACKAGE_ID=package_4fffe7519d18ead82fdc
NEW_ALPHA_RECEIPT_ID=alpha_receipt_002338565d8c4a76a9772539914b0d9b

HERMES_RESOLVED_SAME_OBJECTIVE=YES
HERMES_READ_SAME_RESEARCH_PACKAGE=YES
HERMES_READ_SAME_ALPHA_RECEIPT=YES
NOVA_GROUNDING_MATCH=YES; final live answer matched objective, package, source, Alpha decision/receipt, follow-up, missing evidence, and next action; unrelated CRJ/affiliate state was excluded.
GROUNDING_FIELD_MATCH_RATE=100% of material fields (objective, package, source, follow-up, Alpha receipt, decision, missing evidence, next action).

HERMES_RESEARCH_CERTIFICATION=PASS_REAL
CONTINUOUS_RESEARCH_REACTIVATED=YES; the existing canonical owner `scripts/run_continuous_operating_kernel.py --daemon --interval-seconds 1200` was already running (PID 27632, started 2026-09-18); no second scheduler/runtime was created. Hermes was not treated as certified until the fresh bridge recertification passed.

RESEARCH_MONITOR_VISIBLE=NOT_RUN
RESEARCH_MONITOR_MATCHES_CANONICAL_STATE=NOT_APPLICABLE

FILES_CHANGED=services/nexus_mcp/server.py; scripts/nexus_agent_platform/research_evidence_bridge.py; scripts/nexus_agent_platform/bridge/oracle_hermes_cli.py; scripts/nexus_agent_platform/research_alpha_pipeline.py; scripts/research/research_v2.py; scripts/nexus_agent_platform/governed/persistence.py; services/nexus_mcp/tests/test_server.py; this report.
TESTS_RUN=objective-scoped MCP canary; live Hermes 0.20.6 recertification; fresh Research source and package persistence; model-backed Alpha review; Alpha follow-up reroute after bounded 403/404 source failures; bridge/unit tests.
TEST_RESULTS=PASS_REAL; 25 bridge/MCP/Oracle tests passed with one pre-existing tool-surface test excluded because the runtime registers additional read-only Google tools; live Hermes canonical field cross-check passed.
COMMITS=95ac070e (pushed origin/main)

RAY_ACTION_REQUIRED=NO for Hermes bridge certification; continuous Research remains intentionally off.
TRUE_EXTERNAL_BLOCKERS=NONE for the evidence bridge. The first follow-up candidates returned ordinary 403/404 source failures; strategy changed and the objective continued to Square's current appointment source.
NEXT_MACHINE_ACTION=Keep the existing canonical owner and monitor first-day guardrails; pause only a defective lane, never create a second scheduler, and route objective-scoped follow-ups through the repaired bridge.
