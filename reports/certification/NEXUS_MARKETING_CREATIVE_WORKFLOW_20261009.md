# Nexus Marketing + Creative Workflow Canary — 2026-10-09

## Result

`MARKETING_CREATIVE_WORKFLOW_READY=YES` for the bounded, provider-free internal workflow. This certifies the Marketing + Creative path exercised here; it does not start whole-company certification or authorize publication, spend, email, social, browser publishing, or paid generation.

## Durable campaign

- Campaign: `campaign-marketing-creative-canary-20261009-20042`
- Correlation: `corr_651e94326e9bb8efdec9708b`
- Root: Research test insight with structured evidence reference.
- Durable stages: Research handoff → Marketing strategy → Creative brief → Creative V1 → Marketing `REVISE` → Creative V2 → Marketing `ACCEPT` → approval pending → publishing-ready handoff → TEST performance → Marketing analysis → `ITERATE`.
- Nine workflow jobs completed with nine receipts. Nine durable handoffs have receipt IDs. Two distinct asset IDs were produced.
- The revision count is one. The review decisions are exactly `REVISE`, then `ACCEPT`. The state is `ITERATION_READY` with `PENDING_RAY_APPROVAL`.

## Approval and external-action boundary

The local deterministic renderer was selected explicitly with expected cost zero. The publishing handoff is `BLOCKED_BY_APPROVAL`; it records zero publication attempts. Performance is marked `DATA_CLASS=TEST` and all numerical activity/cost values are zero or null. No provider, spend, email, social, payment, trading, cloud creation, or browser publishing action occurred.

## Failure and recovery

A separate `CREATIVE_QA` failure canary was claimed once with `max_attempts=1` and reached terminal `BLOCKED` with the expected missing-artifact contract failure. It did not silently complete or create another asset job. The performance collection job also exercised expired-lease recovery: one expired claim was recovered, then the job completed on attempt two with one receipt. No duplicate or concurrent claim was observed.

The original canary controller process exited before emitting its summary because it polled PostgREST beyond its own per-process read budget while waiting around scheduled retries. The durable campaign nevertheless completed. The result above is based on independent live durable-job queries and local artifact/handoff records, not on that process exit code. The controller defect was repaired to make a single bounded wait for the next retry time or fail closed when no retry is scheduled. Mocked regression tests cover due-retry waiting, no-retry termination, and excessive-delay rejection. The campaign was not rerun or duplicated.

## Post-canary state

Live queue verification found 9 completed campaign jobs, one terminal failure job, zero active campaign jobs, and zero due campaign jobs. `task_requests` stayed at 636 and `credit_analysis_jobs` stayed at 25. No campaign worker remained. Scheduler and dispatcher are OFF; no Nexus launch agent was loaded.

Focused tests: 15 passed sequentially. No whole-company certification was started.
