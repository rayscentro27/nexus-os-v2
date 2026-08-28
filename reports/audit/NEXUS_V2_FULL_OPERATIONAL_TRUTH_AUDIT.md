# Nexus OS V2 Real-World Operational Truth Audit

Audit date: 2026-08-28  |  Repository HEAD: `6e3a2b3c7f16dce908eeafdedd88c5e9d98d5a4d`

## Executive Truth

TOTAL_LOOPS=19
REAL_OPERATIONAL=0
REAL_OPERATIONAL_INTERNAL_ONLY=3
REAL_PARTIAL=2
IMPLEMENTED_NOT_CONNECTED=0
MISWIRED=8
SIMULATED_PLACEHOLDER=0
DRY_RUN_BY_DESIGN=4
BLOCKED_BY_DESIGN=2
STALE_ONLY=0
CONFIG_ONLY=0
NO_REAL_IMPLEMENTATION=0
UNKNOWN=0

OVERALL_OPERATIONAL_PERCENTAGE=15.8% (3/19; scoped real internal control/diagnostic paths only)

This percentage does not count registry rows, source files, tests, simulated receipts, or preflight evidence. The three counted loops are the previously proven Telegram Operator control transport, the tested Hermes Router behavior, and the bounded System Health diagnostic path. Their evidence is scope-limited and does not prove the named business capabilities surrounding them. Supabase Verification is REAL_PARTIAL because the implementation and authenticated browser preflight exist, but no real Ray-triggered campaign execution exists in this audit.

## Systemic Root Cause

The declarative process registry was treated as an executable topology. Nineteen rows were seeded with the same historical timestamp and `last_status=simulated`; most rows point to `scripts/operations/nexus_active_operator_runner.py`, a generic closed-world runner that discovers attention, writes generic receipts, and does not implement the named workflow for each row. `enabled=true` therefore became conflated with operational readiness.

Historical receipts commonly say `status=completed` while their nested details say `simulated=true`, and commonly say `telegram_triggered=false`. Static reports, local JSON queues, dry-run modes, and passing tests were allowed to resemble runtime proof. Multiple implementation generations then accumulated: real components exist under `scripts/telegram`, `scripts/alpha`, `scripts/client_flow`, `scripts/credit`, `scripts/automation`, `scripts/review`, `scripts/creative`, and governed modules, but the registry was not reconciled to those entrypoints.

The result is not one broken loop; it is a source-of-truth boundary failure. Configuration, implementation, scheduler loading, execution, result verification, and human visibility are separate facts and must not be collapsed into one `last_status` field.

## Mac Runtime Truth

- Hermes Telegram launchd plist exists and points to the repository worker. The observed launchd job was between one-shot runs (`state=not running`), while the latest heartbeat/log showed a healthy no-update dispatch at `2026-08-28T19:52:56Z`.
- Active Operator plist exists and points to the generic runner, but campaign safety keeps Active Operator paused. A readable old heartbeat is not current execution proof.
- `process_registry_spool.jsonl` exists and is large, but its existence proves persistence, not successful execution of each named process.
- Environment configuration names were present in `.env`, `.env.e2e.local`, and/or the runtime environment; values were not printed.
- Governed Supabase server read was reachable during audit, but a selected `process_id` column on `nexus_process_definitions` was rejected because the live table uses `process_key`; this is direct evidence that registry/schema reconciliation is incomplete.
- Supabase `nexus_process_runs` read returned HTTP 206 with rows; no write was attempted.

## 19-Loop Summary

The complete declaration snapshot is preserved in `NEXUS_V2_FULL_OPERATIONAL_TRUTH_AUDIT.json`. `REGISTRY_DECLARATION` below records the material declaration; all requested registry fields were captured there.

### 1. telegram_operator

PURPOSE=Real Telegram operator/control transport.
REGISTRY_DECLARATION=TELEGRAM_OPERATOR; enabled=true; polling; `scripts/telegram/nexus_telegram_bridge.py`; last_status=skipped; last_run_at=2026-08-20T04:04:48Z.
ACTUAL_ENTRYPOINT=Repository Hermes Telegram worker plus Telegram bridge generations.
ACTUAL_TRIGGER=Real authorized Telegram update; proven for the campaign-control scope only.
ACTUAL_IMPLEMENTATION=Connected and real for tested control transport; not proof of every Telegram business command.
DATA_SOURCE=Live Telegram receipt and campaign state for the tested event; other registry state static/simulated.
RUNTIME_STATE=REAL_PASS for tested scope; registry row itself is stale/skipped.
LAST_REAL_EXECUTION=Campaign evidence, not registry runner execution.
AUTONOMOUS_STATE=Loaded one-shot Hermes worker; reboot/recovery not proven.
18_STAGE_SCORE=REAL_PASS 8; NOT_APPLICABLE 10.
PRIMARY_CLASSIFICATION=REAL_OPERATIONAL_INTERNAL_ONLY
DISPOSITION=KEEP
PRIORITY=P0
WHAT_IS_REAL=Authorized Telegram intake, campaign routing, delivery, correlation.
WHAT_IS_FAKE_OR_SIMULATED=Generic registry receipt history.
WHAT_IS_MISWIRED=Registry entry does not point to the current Hermes worker.
WHAT_IS_MISSING=Full command topology proof.
WHAT_MUST_CHANGE=Future registry must name the canonical worker and scope proof.

### 2. hermes_router

PURPOSE=Hermes operational control-object routing.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; on_demand; generic Active Operator runner; last_status=simulated; identical seeded timestamp.
ACTUAL_ENTRYPOINT=Current Hermes Telegram worker and control-object resolver.
ACTUAL_TRIGGER=Real `Status VOICE-001`; proven for that read-only route.
ACTUAL_IMPLEMENTATION=Real tested route exists outside the registered runner.
DATA_SOURCE=Live repair/work-order state and Telegram receipt for tested event.
RUNTIME_STATE=REAL_PASS for tested route; registry declaration is simulated.
LAST_REAL_EXECUTION=Campaign evidence for VOICE-001 status.
AUTONOMOUS_STATE=Worker dispatch loaded; autonomous router topology not fully proven.
18_STAGE_SCORE=REAL_PASS 8; NOT_APPLICABLE 10.
PRIMARY_CLASSIFICATION=REAL_OPERATIONAL_INTERNAL_ONLY
DISPOSITION=KEEP
PRIORITY=P0
WHAT_IS_REAL=Deterministic read-only control-object resolution.
WHAT_IS_FAKE_OR_SIMULATED=Generic registry last_status and receipts.
WHAT_IS_MISWIRED=Registry points to generic runner.
WHAT_IS_MISSING=Complete router command inventory.
WHAT_MUST_CHANGE=Registry/entrypoint reconciliation.

### 3. system_health

PURPOSE=Bounded internal health diagnostic.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; last_status=simulated; identical seeded timestamp.
ACTUAL_ENTRYPOINT=`run_system_health_check` and shared health capability.
ACTUAL_TRIGGER=Real Telegram `/run system_health`; certified bounded path.
ACTUAL_IMPLEMENTATION=Connected internal read-only implementation.
DATA_SOURCE=Live local registry, failure report, governed Supabase telemetry; latest real result DEGRADED.
RUNTIME_STATE=REAL_PASS for bounded execution; registry row stale/simulated.
LAST_REAL_EXECUTION=Real Telegram supplemental retest, not run during this audit.
AUTONOMOUS_STATE=Manual worker path; Active Operator paused.
18_STAGE_SCORE=REAL_PASS 8; BLOCKED_BY_DESIGN/NOT_APPLICABLE 10.
PRIMARY_CLASSIFICATION=REAL_OPERATIONAL_INTERNAL_ONLY
DISPOSITION=KEEP
PRIORITY=P0
WHAT_IS_REAL=Health process execution, report, receipt, Telegram visibility.
WHAT_IS_FAKE_OR_SIMULATED=Registry historical status.
WHAT_IS_MISWIRED=Registry still advertises generic runner.
WHAT_IS_MISSING=Fresh autonomous scheduler proof.
WHAT_MUST_CHANGE=Separate process truth from certification history.

### 4. supabase_verification

PURPOSE=Manual governed Supabase/browser/RLS verification.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; last_status=simulated; identical seeded timestamp.
ACTUAL_ENTRYPOINT=Bounded runner plus new narrow Playwright spec.
ACTUAL_TRIGGER=Real Ray Telegram command is required and was not executed in this audit.
ACTUAL_IMPLEMENTATION=Connected implementation; browser preflight passed using existing Persona A.
DATA_SOURCE=Live governed read and authenticated browser preflight; no campaign evidence.
RUNTIME_STATE=Preflight PASS; real campaign execution absent.
LAST_REAL_EXECUTION=None for campaign purposes.
AUTONOMOUS_STATE=Manual only.
18_STAGE_SCORE=REAL_PARTIAL; real trigger/receipt/completion campaign stages missing.
PRIMARY_CLASSIFICATION=REAL_PARTIAL
DISPOSITION=KEEP
PRIORITY=P1
WHAT_IS_REAL=Server read, UI login, session persistence, authenticated read, own-scope/cross-tenant/admin denial preflight.
WHAT_IS_FAKE_OR_SIMULATED=Old July receipts.
WHAT_IS_MISWIRED=Registry still generic.
WHAT_IS_MISSING=Fresh Ray-triggered correlated evidence.
WHAT_MUST_CHANGE=Run the human-gated real trigger later.

### 5. research_intelligence

PURPOSE=Research collection/intelligence.
REGISTRY_DECLARATION=DRY_RUN; enabled=true; manual; generic runner; last_status=simulated.
ACTUAL_ENTRYPOINT=`scripts/run_nexus_research_cycle.py`, `scripts/hermes/hermes_web_search.py`, research loops.
ACTUAL_TRIGGER=Manual/scripts and provider-specific paths, not the registry runner.
ACTUAL_IMPLEMENTATION=Real code exists elsewhere; registry disconnected and dry-run.
DATA_SOURCE=Mixed cached/static/provider-dependent; no fresh real loop proof.
RUNTIME_STATE=DRY_RUN/SIMULATED.
LAST_REAL_EXECUTION=Not established.
AUTONOMOUS_STATE=No verified scheduler execution.
18_STAGE_SCORE=DRY_RUN or MISWIRED for execution/trigger/receipt; NOT_APPLICABLE only where no claim exists.
PRIMARY_CLASSIFICATION=DRY_RUN_BY_DESIGN
DISPOSITION=REWIRE
PRIORITY=P2
WHAT_IS_REAL=Research implementation components.
WHAT_IS_FAKE_OR_SIMULATED=Registry receipts and dry-run mode.
WHAT_IS_MISWIRED=Generic runner assignment.
WHAT_IS_MISSING=Canonical provider/data/freshness contract.
WHAT_MUST_CHANGE=Reconcile registry to one safe read-only entrypoint.

### 6. repo_intelligence

PURPOSE=Repository intelligence.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=Repository study/index/report scripts.
ACTUAL_TRIGGER=Ad hoc/manual scripts.
ACTUAL_IMPLEMENTATION=Components exist, registry not connected.
DATA_SOURCE=Local repository/static reports.
RUNTIME_STATE=Simulated registry.
LAST_REAL_EXECUTION=Not established.
AUTONOMOUS_STATE=No verified scheduler.
18_STAGE_SCORE=MISWIRED/CONFIG_ONLY except read-only implementation stages.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P2
WHAT_IS_REAL=Repository analysis code.
WHAT_IS_FAKE_OR_SIMULATED=Generic receipts.
WHAT_IS_MISWIRED=Runner path.
WHAT_IS_MISSING=Fresh execution and receipt lineage.
WHAT_MUST_CHANGE=Canonical entrypoint.

### 7. alpha_intake

PURPOSE=Alpha intake.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; on_demand; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/alpha/alpha_telegram_worker.py` and alpha modules.
ACTUAL_TRIGGER=Separate Alpha Telegram/runtime paths.
ACTUAL_IMPLEMENTATION=Real Alpha components exist but are orphaned from this row.
DATA_SOURCE=Mixed runtime/context and research state.
RUNTIME_STATE=Simulated registry.
LAST_REAL_EXECUTION=Not established for this registry loop.
AUTONOMOUS_STATE=Separate plist/script generations; not proven here.
18_STAGE_SCORE=MISWIRED/STALE_EVIDENCE.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P1
WHAT_IS_REAL=Alpha code.
WHAT_IS_FAKE_OR_SIMULATED=Registry history.
WHAT_IS_MISWIRED=Generic runner.
WHAT_IS_MISSING=Canonical connection and safe authority proof.
WHAT_MUST_CHANGE=Reconcile or retire duplicate path.

### 8. client_portal_paywall_access

PURPOSE=Client portal paywall access.
REGISTRY_DECLARATION=BLOCKED; enabled=false; manual; generic runner; blocked.
ACTUAL_ENTRYPOINT=Client portal/payment and access code exists.
ACTUAL_TRIGGER=Gated application flow.
ACTUAL_IMPLEMENTATION=Not enabled; no real production access proof.
DATA_SOURCE=Static/test/payment configuration.
RUNTIME_STATE=BLOCKED by design.
LAST_REAL_EXECUTION=None.
AUTONOMOUS_STATE=Not scheduled.
18_STAGE_SCORE=BLOCKED_BY_DESIGN for authority/external effect/execution.
PRIMARY_CLASSIFICATION=BLOCKED_BY_DESIGN
DISPOSITION=LEAVE_BLOCKED
PRIORITY=P1
WHAT_IS_REAL=Some client/payment code.
WHAT_IS_FAKE_OR_SIMULATED=No production operational proof.
WHAT_IS_MISWIRED=Registry points generic runner despite blocked mode.
WHAT_IS_MISSING=Approved payment/access activation.
WHAT_MUST_CHANGE=No change during audit.

### 9. client_portal_status

PURPOSE=Client portal status/readiness.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=Client portal pages, `scripts/client_flow`, Supabase client modules.
ACTUAL_TRIGGER=Frontend/session or manual report scripts.
ACTUAL_IMPLEMENTATION=Real read paths exist; registry disconnected.
DATA_SOURCE=Supabase plus synthetic/client test data and static fallbacks.
RUNTIME_STATE=Simulated registry; browser capability not this loop’s real proof.
LAST_REAL_EXECUTION=Not established.
AUTONOMOUS_STATE=No verified loop scheduler.
18_STAGE_SCORE=MISWIRED; authenticated stages IMPLEMENTED_NOT_PROVEN.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P1
WHAT_IS_REAL=Frontend and client-flow code.
WHAT_IS_FAKE_OR_SIMULATED=Static fallback/report history.
WHAT_IS_MISWIRED=Generic runner.
WHAT_IS_MISSING=Canonical read-only status entrypoint and fresh proof.
WHAT_MUST_CHANGE=Connect one source of truth.

### 10. command_center_health

PURPOSE=Command center health.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=Command-center feeder/read-model and UI modules.
ACTUAL_TRIGGER=Manual feeder/build paths.
ACTUAL_IMPLEMENTATION=Separate implementation exists; registry miswired.
DATA_SOURCE=Local read models/static runtime reports.
RUNTIME_STATE=Simulated registry.
LAST_REAL_EXECUTION=Not established.
AUTONOMOUS_STATE=No verified schedule.
18_STAGE_SCORE=MISWIRED/STALE_EVIDENCE.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P0
WHAT_IS_REAL=Read-model/feeder code.
WHAT_IS_FAKE_OR_SIMULATED=Generic runner receipts.
WHAT_IS_MISWIRED=Registry target.
WHAT_IS_MISSING=Fresh connected health run.
WHAT_MUST_CHANGE=Reconcile control-plane source.

### 11. creative_quality_loop

PURPOSE=Creative quality review.
REGISTRY_DECLARATION=DRY_RUN; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/creative/*`, `scripts/runner_handlers/creative_handlers.py`.
ACTUAL_TRIGGER=Internal creative scripts/review flows.
ACTUAL_IMPLEMENTATION=Real draft/review code, intentionally non-publishing.
DATA_SOURCE=Internal drafts/assets and static reports.
RUNTIME_STATE=DRY_RUN by design.
LAST_REAL_EXECUTION=No real external publication, as safety requires.
AUTONOMOUS_STATE=No operational scheduler proof.
18_STAGE_SCORE=DRY_RUN; external effect BLOCKED_BY_DESIGN.
PRIMARY_CLASSIFICATION=DRY_RUN_BY_DESIGN
DISPOSITION=KEEP
PRIORITY=P3
WHAT_IS_REAL=Internal quality/draft components.
WHAT_IS_FAKE_OR_SIMULATED=Publication/external-effect implication.
WHAT_IS_MISWIRED=Registry generic runner.
WHAT_IS_MISSING=Explicit draft-only contract.
WHAT_MUST_CHANGE=Do not claim publishing operation.

### 12. credit_business_funding_readiness

PURPOSE=Credit/business/funding readiness delivery.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/credit/*`, `scripts/client_flow/build_funding_readiness.py`, Supabase workflow/UI.
ACTUAL_TRIGGER=Client/admin workflow and manual scripts.
ACTUAL_IMPLEMENTATION=Substantial real components exist outside registry runner.
DATA_SOURCE=Supabase/client data plus fixtures/static readiness artifacts.
RUNTIME_STATE=Simulated registry.
LAST_REAL_EXECUTION=Not established as this named loop.
AUTONOMOUS_STATE=No verified scheduler.
18_STAGE_SCORE=MISWIRED; data/auth stages IMPLEMENTED_NOT_PROVEN.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P1
WHAT_IS_REAL=Credit/readiness engines and client delivery code.
WHAT_IS_FAKE_OR_SIMULATED=Registry run history and fixtures used in some paths.
WHAT_IS_MISWIRED=Generic runner.
WHAT_IS_MISSING=Fresh real client-safe workflow proof.
WHAT_MUST_CHANGE=Prioritize canonical delivery path.

### 13. daily_monitor

PURPOSE=Daily monitoring/reporting.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/operations/nexus_daily_monitor.py`, `scripts/run_nexus_daily_monitor.py`.
ACTUAL_TRIGGER=Separate script/manual schedule generations.
ACTUAL_IMPLEMENTATION=Real component exists elsewhere; registry path is wrong.
DATA_SOURCE=Local registry/reports, likely cached/static for historical output.
RUNTIME_STATE=Simulated registry.
LAST_REAL_EXECUTION=Not established.
AUTONOMOUS_STATE=No verified current scheduler.
18_STAGE_SCORE=MISWIRED/STALE_EVIDENCE.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P2
WHAT_IS_REAL=Daily monitor script.
WHAT_IS_FAKE_OR_SIMULATED=Generic receipt history.
WHAT_IS_MISWIRED=Registry runner.
WHAT_IS_MISSING=Connected fresh report proof.
WHAT_MUST_CHANGE=Choose canonical daily monitor.

### 14. marketing_content_pipeline

PURPOSE=Marketing content pipeline.
REGISTRY_DECLARATION=DRY_RUN; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/marketing/*`, creative/content generators.
ACTUAL_TRIGGER=Internal draft generators.
ACTUAL_IMPLEMENTATION=Draft-generation code exists; external publishing is gated.
DATA_SOURCE=Draft/static/cache data.
RUNTIME_STATE=DRY_RUN by design.
LAST_REAL_EXECUTION=No external publication permitted.
AUTONOMOUS_STATE=No verified scheduler.
18_STAGE_SCORE=DRY_RUN; external effect BLOCKED_BY_DESIGN.
PRIMARY_CLASSIFICATION=DRY_RUN_BY_DESIGN
DISPOSITION=KEEP
PRIORITY=P3
WHAT_IS_REAL=Internal draft pipeline.
WHAT_IS_FAKE_OR_SIMULATED=Publication implication.
WHAT_IS_MISWIRED=Generic registry runner.
WHAT_IS_MISSING=Explicit draft-only operational contract.
WHAT_MUST_CHANGE=Do not claim outbound operation.

### 15. notebooklm_import_status

PURPOSE=NotebookLM import status.
REGISTRY_DECLARATION=DRY_RUN; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/intake/notebooklm_connector.py` and notebooklm scripts.
ACTUAL_TRIGGER=Manual/import tooling.
ACTUAL_IMPLEMENTATION=Connector exists; registry disconnected and dry-run.
DATA_SOURCE=Local export/cache bundles.
RUNTIME_STATE=DRY_RUN/SIMULATED.
LAST_REAL_EXECUTION=Not established.
AUTONOMOUS_STATE=No verified schedule.
18_STAGE_SCORE=DRY_RUN/MISWIRED.
PRIMARY_CLASSIFICATION=DRY_RUN_BY_DESIGN
DISPOSITION=REWIRE
PRIORITY=P3
WHAT_IS_REAL=Import code.
WHAT_IS_FAKE_OR_SIMULATED=Registry receipts and historical status.
WHAT_IS_MISWIRED=Generic runner.
WHAT_IS_MISSING=Fresh import proof and source freshness.
WHAT_MUST_CHANGE=Reconcile if retained.

### 16. ray_review_queue

PURPOSE=Ray human review queue.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/review/build_ray_review_queue.py`, communication/review modules.
ACTUAL_TRIGGER=Internal report/build scripts and UI.
ACTUAL_IMPLEMENTATION=Real queue builders exist elsewhere; registry miswired.
DATA_SOURCE=Local queues/reports and approval state.
RUNTIME_STATE=Simulated registry.
LAST_REAL_EXECUTION=Not established for this row.
AUTONOMOUS_STATE=No verified scheduler.
18_STAGE_SCORE=MISWIRED; human visibility IMPLEMENTED_NOT_PROVEN.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P0
WHAT_IS_REAL=Review queue code and human gate machinery.
WHAT_IS_FAKE_OR_SIMULATED=Generic runner history.
WHAT_IS_MISWIRED=Registry target.
WHAT_IS_MISSING=One canonical queue/report receipt.
WHAT_MUST_CHANGE=Reconcile human control-plane path.

### 17. recovery

PURPOSE=Recovery inspection.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; manual; `scripts/operations/nexus_recovery_check.py`; simulated.
ACTUAL_ENTRYPOINT=Recovery check script.
ACTUAL_TRIGGER=Manual/read-only inspection.
ACTUAL_IMPLEMENTATION=Correctly connected read-only checker, but current registry evidence is simulated/stale.
DATA_SOURCE=Local runtime/config/report state.
RUNTIME_STATE=REAL_PARTIAL implementation; no fresh audit canary run.
LAST_REAL_EXECUTION=Not established in this audit.
AUTONOMOUS_STATE=No reboot recovery proof; Active Operator paused.
18_STAGE_SCORE=REAL_PARTIAL for inspection; NOT_APPLICABLE for restart/recovery execution.
PRIMARY_CLASSIFICATION=REAL_PARTIAL
DISPOSITION=KEEP
PRIORITY=P0
WHAT_IS_REAL=Read-only recovery inspection code.
WHAT_IS_FAKE_OR_SIMULATED=Registry status/receipts.
WHAT_IS_MISWIRED=No major entrypoint mismatch.
WHAT_IS_MISSING=Fresh real receipt and reboot recovery proof.
WHAT_MUST_CHANGE=Separate inspection from recovery execution claim.

### 18. stripe_test_paywall

PURPOSE=Stripe test paywall.
REGISTRY_DECLARATION=SANDBOX_TEST; enabled=false; manual; generic runner; blocked.
ACTUAL_ENTRYPOINT=Payment test scripts and approval lanes.
ACTUAL_TRIGGER=Explicit gated test flow.
ACTUAL_IMPLEMENTATION=Test code exists, disabled and not operational.
DATA_SOURCE=Demo/test Stripe configuration.
RUNTIME_STATE=BLOCKED by design.
LAST_REAL_EXECUTION=None.
AUTONOMOUS_STATE=Not scheduled.
18_STAGE_SCORE=BLOCKED_BY_DESIGN for authority/effect/execution.
PRIMARY_CLASSIFICATION=BLOCKED_BY_DESIGN
DISPOSITION=LEAVE_BLOCKED
PRIORITY=P4
WHAT_IS_REAL=Sandbox/test code.
WHAT_IS_FAKE_OR_SIMULATED=Production operational implication.
WHAT_IS_MISWIRED=Generic runner assignment.
WHAT_IS_MISSING=Separate approved sandbox test contract.
WHAT_MUST_CHANGE=No change during audit.

### 19. work_orders

PURPOSE=Governed work-order management.
REGISTRY_DECLARATION=ACTIVE_INTERNAL; enabled=true; on_demand; generic runner; simulated.
ACTUAL_ENTRYPOINT=`scripts/nexus_agent_platform/governed/work_orders.py` and governed APIs.
ACTUAL_TRIGGER=Hermes/governed request paths.
ACTUAL_IMPLEMENTATION=Real work-order module exists; registry runner is not its canonical entrypoint.
DATA_SOURCE=Local governed queue/state.
RUNTIME_STATE=Simulated registry.
LAST_REAL_EXECUTION=Real work-order records exist, but no loop-specific fresh proof.
AUTONOMOUS_STATE=No autonomous execution proof.
18_STAGE_SCORE=MISWIRED; authority/receipt IMPLEMENTED_NOT_PROVEN.
PRIMARY_CLASSIFICATION=MISWIRED
DISPOSITION=REWIRE
PRIORITY=P0
WHAT_IS_REAL=Governed work-order APIs.
WHAT_IS_FAKE_OR_SIMULATED=Generic Active Operator receipt history.
WHAT_IS_MISWIRED=Registry runner.
WHAT_IS_MISSING=Canonical loop entrypoint and fresh lineage proof.
WHAT_MUST_CHANGE=Make work-order control-plane ownership explicit.

## Retire/Merge Candidates

- `stripe_test_paywall`: retain only as a clearly separate development/sandbox gate; do not count as an operational loop.
- `client_portal_paywall_access`: merge with the canonical client/revenue access control plane if ever activated; do not maintain a standalone fake loop.
- `marketing_content_pipeline` and `creative_quality_loop`: merge draft/quality responsibilities or explicitly keep both as non-publishing internal lanes.
- `notebooklm_import_status`: merge into research/intake if it remains an import adapter rather than a standalone workflow.

## Repair Order (recommendation only; not executed)

1. Establish a new operational truth schema and validator; do not infer execution from the current registry.
2. Reconcile P0 control-plane paths: Telegram/Hermes, work orders, review queue, command-center health, recovery.
3. Reconcile P1 client/revenue paths: client portal status, credit/business/funding readiness, Supabase verification.
4. Reconcile P2 leverage paths: daily monitor, repo intelligence, research and Alpha intake.
5. Keep draft-only, sandbox-only, and blocked-by-design lanes explicitly outside operational scoring.
6. Require fresh purpose-appropriate real evidence before any row is marked operational.

## Future Operational Registry Replacement Design

Every process should expose: `process_id`, `canonical_entrypoint`, `trigger`, `execution_mode`, `dependency_contract`, `authority_contract`, `data_source_contract`, `output_contract`, `receipt_contract`, `freshness_contract`, `health_contract`, `scheduler_contract`, `real_world_proof_required`, `latest_real_run_id`, `latest_real_run_at`, `latest_real_result`, `current_operational_state`, `simulation_allowed`, `simulation_state`, and `test_fixture_allowed`.

Validation rule: **No process may be marked operational without fresh real execution evidence appropriate to its purpose.**

## Safety

Active Operator remains paused. No payments, Stripe charges, email, social publishing, deployment, client production mutation, credential rotation, service restart, Voice repair, Hermes upgrade, or autonomous engineering change was performed. No campaign certification or campaign advancement was performed.
