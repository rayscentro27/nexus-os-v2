# Bounded Research-only execution contract

## Scope

`RESEARCH_ONLY` is an explicit assignment intent for one source-grounded Research result. It is not inferred from question wording and does not change `RESEARCH_MISSION`. It requires the ordinary durable job, host and State v2 readiness gates, governance reservation, Research case engine, public-source validation, egress budget, worker supervision, and receipt path.

The worker accepts this path only for a Research `RESEARCH_INTAKE` job whose durable source is `NOVA_MCP_RESEARCH_ASSIGNMENT` and whose hydrated intent is exactly `RESEARCH_ONLY`. A missing or rejected public source is a bounded Research failure with a compact State v2 result when assignment identity is available; capacity waits use the existing retryable lifecycle.

## Execution graph

| Stage | Input | Output | Next stage | Parent child | Independent | Parent terminal |
|---|---|---|---|---|---|---|
| MCP assignment | explicit intent, objective, question, optional source URL | queue item and `RESEARCH_INTAKE` durable job | worker claim | No | Yes | No |
| Worker gates and governance | exact claimed job and hydrated work item | validated execution envelope and reservation | case open | No | No | No |
| Case open/join | objective, project/work ID, primary question | canonical Research case or capacity wait | one bounded source read | No | No | No |
| Source read | validated public URL | extracted bounded text and URL evidence reference | compact finding persistence | No | No | No |
| Research result persistence | answer, evidence references, exact case question | State v2 case update and compact result record | terminal job receipt | No | No | Yes, for this bounded job |
| Job completion | compact result and successful State v2 receipt | `COMPLETED`, cleared lease, durable receipt | stop | No | No | Yes |

The ordinary `RESEARCH_MISSION` path remains: MCP assignment → case intake → parent continuation child → `SOURCE_UNDERSTANDING` → `KNOWLEDGE_RECONCILIATION` → `ADVISOR_REVIEW` → question generation/follow-up → `NEEDLE_REVIEW` → synthesis/routing/handoff. `research_parent_workflow.WORKFLOW` and `consume_child_result` are not entered by `RESEARCH_ONLY`.

## Research-only result boundary

- Start: after the normal worker has passed claim, host, State v2 readiness, execution contract, egress, governance, route, work-item, and intent checks.
- End: after the real case has been opened/joined, one validated public URL has been read, the matching case question and source-grounded finding have been persisted, and the compact result record has a State v2 receipt.
- The case is held at `AWAITING_RAY_DECISION` with `continue_research=false`; no automatic follow-up, Advisor, Needle, or other child is queued.
- The job ends `COMPLETED`; the work item ends `COMPLETE`; lease is cleared; the normal worker supervision and durable receipt remain active.

## Handoff record

Schema: `nexus.research-only-handoff.v1`.

Fields: `job_id`, `objective_id`, `project_id`, `case_id`, `question`, concise `summary`, `key_findings`, `evidence_references`, `unanswered_questions`, `recommended_next_research_action`, `result_status`, and `recorded_at`.

Bounds: 8 KiB encoded record; 1,200-character summary; five evidence references of at most 300 characters each; five unanswered questions of at most 300 characters each. Source bodies and conversation transcripts are excluded. The public response is capped at 1 MB; there is one source-adapter invocation maximum.

## Roles

- Research collects attributable evidence and answers the assigned question.
- Needle identifies material unanswered questions, determines whether more investigation is needed, and routes unresolved material questions so action can be taken.
- Advisor interprets findings, talks with Ray, challenges assumptions, recommends action, and determines direction.

The bounded canary proves only Research. It does not replace or remove Needle or Advisor from the normal parent workflow.

## Failure behavior

`WAITING_FOR_CAPACITY` uses the existing `WAITING` work item and `FAILED_RETRYABLE`/`BLOCKED` job policy with lease/reservation cleanup. Host-gate and State v2 readiness failures stay `BLOCKED`. Rejected or unavailable source reads persist an explicit compact failure result and do not create continuation work. Unexpected exits use the existing exact-job recovery and supervisor metadata path.
