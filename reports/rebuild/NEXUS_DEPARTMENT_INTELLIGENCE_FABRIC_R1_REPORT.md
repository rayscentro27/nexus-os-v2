# Nexus Department Intelligence Fabric R1

Generated 2026-09-03. This campaign extended the existing Alpha Research and
governed persistence paths; it did not create a second queue, router, objective
engine, Research scheduler, or Alpha system.

## Executive Result

`DEPARTMENT_INTELLIGENCE_FABRIC_R1=PASS`.

The universal fabric is now implemented and tested. Every required partial
department can create a correlated Research request, receive an Alpha-reviewed
result or a targeted follow-up, and resume its original objective. Every
required department can also submit a result feedback envelope that is routed
through Research/Alpha before the next recommendation.

The proof is primarily Level 1 engineering/integration evidence. One SEO
request also used six fresh public Brave search results through the canonical
fabric. This proves the service path, not business success or revenue.

## Audit Report Findings

The prior audit identified two specific gaps:

1. Existing Research jobs had objective/request fields, but no universal
   department-owned envelope carrying department, goal, work-order, knowledge
   gap, freshness, result, follow-up, and resume state.
2. Existing department receipts and specialized feedback stores had no single
   result envelope that every department could submit for Research/Alpha
   interpretation and objective continuation.

The prior report also found two overlapping department registry views. This
campaign did not rewrite those registries; the new fabric validates the
canonical logical department IDs while preserving existing routing and
execution ownership.

## Research Service Root Cause

`MISSING_UNIVERSAL_CORRELATION_ENVELOPE_AND_FULL_DEPARTMENT_COVERAGE`.

The underlying Research/Alpha implementation was usable. The failure was at
the integration boundary: `submit_alpha_request` and `build_research_job`
could accept Research work, but departments could not consistently carry
`objective_id`, `parent_goal_id`, `work_order_id`, `knowledge_gap`, desired
evidence, and a resume/follow-up state through the canonical lifecycle.

## Result Feedback Root Cause

`SPECIALIZED_RESULT_STORES_WITHOUT_A_SHARED_RESEARCH_ALPHA_FEEDBACK_ENVELOPE`.

Creative, trading, opportunity, finance, and operating paths already persisted
some results, but there was no common result record containing action, result,
measurement, evidence level, knowledge implication, Alpha state, and next
recommendation. Consequently, full-company feedback coverage could not be
proven without inventing department-specific adapters.

## Existing Architecture Reused

The repair is implemented in:

- `scripts/nexus_agent_platform/intelligence_fabric.py`
- `scripts/nexus_agent_platform/alpha_research.py` via `build_research_job` and
  `run_alpha_research`
- `scripts/nexus_agent_platform/governed/persistence.py` via append-only
  `research_requests` and `result_feedback` collections
- existing department/work-order/objective IDs, capability authority, and
  Research heartbeat

The two new collections are persistence for the missing canonical envelopes,
not a second task queue. They are append-only and correlated to the existing
queue/work-order/objective records.

## Research Request Path

```text
department
  → build_research_request()
  → governed research_requests persistence
  → existing Alpha build_research_job()
  → existing Alpha run_alpha_research()
  → Alpha decision
  → READY_TO_RESUME or FOLLOW_UP_REQUIRED
  → original department resume
```

The envelope carries `request_id`, `department`, `objective_id`,
`parent_goal_id`, `work_order_id`, `question`, `knowledge_gap`, reason,
desired evidence, risk/consequence, freshness, priority, Research status,
Alpha status, result reference, next action, follow-up ID, and department
resume state.

`CANONICAL_RESEARCH_REQUEST_PATH=PASS_REAL`.

## Alpha Integration

Alpha is not bypassed. `run_research_request` creates the existing Alpha job,
passes canonical evidence, records the Alpha receipt/reference, and maps the
Alpha result to `QUALIFIED` or `MORE_RESEARCH_REQUIRED`.

When evidence is weak, the fabric automatically persists a targeted follow-up
request for the same department/objective/work order. The parent objective is
not failed or closed.

`ALPHA_IN_UNIVERSAL_RESEARCH_PATH=PASS_REAL`.

The live SEO proof used six public Brave search results and produced Alpha
receipt `alpha-receipt-4a7500a999374795` for request
`research_request_f00d6e5b32a073c0f0e7` with decision `QUALIFIED`.

## Department Resume

`resume_department()` requires `READY_TO_RESUME`, persists `RESUMED`, retains
all objective/goal/work-order correlation, and records the department’s next
action. Research completion therefore does not masquerade as department
objective completion.

`DEPARTMENT_RESUME_AFTER_RESEARCH=PASS_REAL`.

## Result Feedback Path

```text
department action/result
  → record_result_feedback()
  → governed result_feedback persistence
  → Research interpretation request
  → existing Alpha Research evaluation
  → COMPLETE + QUALIFIED or MORE_RESEARCH_REQUIRED
  → next recommendation / targeted follow-up
```

The result envelope contains `result_id`, department, objective, parent goal,
work order, action, result, evidence, measurement, evidence level,
success/failure/partial outcome, what changed, unexpected result, knowledge
implication, Research state, Alpha state, next recommendation, and follow-up
reference.

`CANONICAL_RESULT_FEEDBACK_PATH=PASS_REAL`.

## Failure Feedback

Empty or insufficient evidence produces `MORE_RESEARCH_REQUIRED` and a
targeted request; it does not fail the parent objective. This was tested with
the Marketing department. A successful Systems benchmark feedback record was
also routed through Research and Alpha, with the objective ID preserved.

`FAILED_RESULT_TO_RESEARCH=PASS_REAL`.

## Universal Department Proof

The focused test exercised all 11 previously partial departments:

`ALPHA`, `HERMES_NOVA`, `SYSTEMS_ENGINEERING`, `CREATIVE`, `MARKETING`, `SEO`,
`CLYDE_CREDIT`, `FUNDING`, `FINANCE`, `BUSINESS_OPPORTUNITY`, and
`TRADING_RESEARCH`.

Each completed:

`department → Research request → existing Alpha → returned intelligence →
department resume`.

Evidence classification: `LEVEL_1_SYNTHETIC / ENGINEERING_PROOF` for the
bounded fixtures. The SEO proof additionally used real public search input;
it remains research evidence and does not imply an external business result.

`DEPARTMENTS_CONNECTED_TO_RESEARCH=11`.
`DEPARTMENTS_CONNECTED_TO_RESULT_FEEDBACK=11`.

## Browser / Computer Use

The capability registry already includes read-only `curl`, Playwright, and
public web research paths with external effects denied by default. The live
SEO fabric proof resolved through the existing public Brave CLI/API path and
did not need authentication, payments, publication, or outreach. The fallback
order remains existing code → CLI/API/MCP → browser → safe configuration →
Research → capability gap → Ray only for human-only boundaries.

`BROWSER_CAPABILITY_RESOLUTION_PATH=PASS_REAL`.

No browser failure was treated as terminal, and no authentication was bypassed.

## Blocker Recovery

No report-only blocker was emitted. Weak evidence was converted to a targeted
follow-up request, and the originating objective remained active.

`REPORT_ONLY_BLOCKER_BEHAVIOR=PROHIBITED`.

No true Ray blocker exists. External publication, outreach, spending, live
financial actions, client contact, and production mutation remain approval or
safety boundaries.

## Research Continuity

After implementation and tests, persisted runtime state still reports:

```text
RESEARCH_ENABLED=YES
RESEARCH_HEARTBEAT=ACTIVE
RESEARCH_SCHEDULER=ACTIVE_DAEMON
NEXT_WAKE=2026-09-03T16:56:01.607061+00:00
```

`RESEARCH_CONTINUITY=PASS_REAL`.

## Remaining Department Gaps

The fabric connects departments to intelligence; it does not make each
department complete. Creative, Marketing, SEO, Clyde, Funding, Finance,
Business Opportunity, Trading Research, Hermes Nova, Systems, and Alpha retain
the partial capability/runtime/integration gaps recorded in the prior audit.
Trading remains paper/demo only. Public actions, customer contact, payments,
and financial authority remain gated.

## Next Phase

`CREATIVE_DEPARTMENT_CAPABILITY_RECOVERY_AND_EXPANSION`.

Build Creative against the universal envelopes first: brief → concept → critic
→ result feedback → Research/Alpha learning. Then proceed to Marketing and SEO
without introducing department-specific orchestration.

## Git

Starting state: `START_HEAD=bda7c085b323ba2206a79e6a7c22ee8f24cd2774`,
`origin/main=33c661559a37fcbda34adb98eb61c304fd793131`, branch `main`,
`WORKTREE_ENTRY_COUNT_BEFORE=10239`. Existing unrelated worktree changes were
preserved. Only the two shared-contract source files, their focused test, and
this report are task-scoped; no reset, clean, broad staging, or secret exposure
was performed.

## Focused Verification

```text
test_intelligence_fabric.py: 3 passed
test_alpha_research_intelligence.py: 5 passed
test_alpha_external_intelligence.py: 8 passed
```

The existing Python department-router suite still has two pre-existing
front-brain semantic failures (`NO_EXECUTION` vs `UNKNOWN_INTENT` and
`ANSWERED` vs `BLOCKED`) plus an empty Bearer-header log. Those are separate
router/test issues and were not silently reclassified as fabric failures.

## Final Contract

```text
DEPARTMENT_INTELLIGENCE_FABRIC_R1=PASS
RESEARCH_SERVICE_FAILURE_ROOT_CAUSE=MISSING_UNIVERSAL_CORRELATION_ENVELOPE_AND_FULL_DEPARTMENT_COVERAGE
RESULT_FEEDBACK_FAILURE_ROOT_CAUSE=SPECIALIZED_RESULT_STORES_WITHOUT_A_SHARED_RESEARCH_ALPHA_FEEDBACK_ENVELOPE
CROSS_DEPARTMENT_WORK_CONTRACT=PASS_REAL
CANONICAL_RESEARCH_REQUEST_PATH=PASS_REAL
ALPHA_IN_UNIVERSAL_RESEARCH_PATH=PASS_REAL
DEPARTMENT_RESUME_AFTER_RESEARCH=PASS_REAL
CANONICAL_RESULT_FEEDBACK_PATH=PASS_REAL
FAILED_RESULT_TO_RESEARCH=PASS_REAL
UNIVERSAL_RESEARCH_SERVICE=PASS_REAL
UNIVERSAL_RESULT_FEEDBACK=PASS_REAL
BROWSER_CAPABILITY_RESOLUTION_PATH=PASS_REAL
REPORT_ONLY_BLOCKER_BEHAVIOR=PROHIBITED
RESEARCH_CONTINUITY=PASS_REAL
RESEARCH_HEARTBEAT=ACTIVE
RESEARCH_SCHEDULER=ACTIVE
DEPARTMENTS_CONNECTED_TO_RESEARCH=11
DEPARTMENTS_CONNECTED_TO_RESULT_FEEDBACK=11
RESEARCH=READY
ALPHA=PARTIAL
HERMES_NOVA=PARTIAL
SYSTEMS_ENGINEERING=PARTIAL
CREATIVE=PARTIAL
MARKETING=PARTIAL
SEO=PARTIAL
CLYDE_CREDIT=PARTIAL
FUNDING=PARTIAL
FINANCE=PARTIAL
BUSINESS_OPPORTUNITY=PARTIAL
TRADING_RESEARCH=PARTIAL
TRUE_RAY_BLOCKERS=NONE
NEXT_RECOMMENDED_PHASE=CREATIVE_DEPARTMENT_CAPABILITY_RECOVERY_AND_EXPANSION
```
