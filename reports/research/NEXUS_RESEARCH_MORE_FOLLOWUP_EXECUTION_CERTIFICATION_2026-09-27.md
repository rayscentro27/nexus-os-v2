# Research More Follow-up Execution Certification

Date: 2026-09-27

## Result

The former stop point was a real implementation gap: Alpha `RESEARCH_MORE`
created a queue projection, but did not create a durable owned Research request.
The queue normalizer also dropped department ownership metadata. Consequently,
the work was visible but not executable by the normal Research worker.

The repair keeps the existing Research scheduler, queue, worker, Alpha bridge,
and handoff path. Each actionable return now has a durable request and queue
projection with `owner=RESEARCH`, department/lane, missing evidence, preferred
and fallback source classes, parent Alpha lineage, return target, retry state,
and next action. Duplicate projections from the first repair pass were marked
`SUPERSEDED` for auditability; no records were deleted.

## Real worker proof

Systems / Needle-Jev was claimed by the existing `research_operator_worker`,
acquired bounded GitHub evidence, completed a Research package, and created a
second Alpha receipt tied to `proactive-canary-systems-capability` and the
original Alpha receipt. Alpha returned `RESEARCH_MORE` again because the GitHub
search result did not establish detailed identity, licensing, compatibility, or
benchmark evidence. A new owned follow-up was persisted.

GoClear and Revenue follow-ups also executed through the same worker and
returned to Alpha. Both remained `RESEARCH_MORE` with explicit remaining gaps.

Trading’s original `REJECT` was not rerun. A new bounded question requested a
concrete candidate. The first GitHub fallback failed with HTTP 404; the worker
persisted `FAILED_RETRYABLE` and created a strategy-changing fallback. The next
bounded public-signal path reached Alpha `TEST` and created a durable Trading
handoff with no external action allowed. The evidence did not contain enough
published strategy rules to claim a concrete Trading strategy, so no such claim
is made.

## Lineage

`original finding → Alpha receipt → research_followup request → owned queue item
→ worker claim/execution → evidence package → Alpha second receipt → next
disposition` is present for the executed cases.

## Safety

No live trading, purchases, paid actions, publications, customer messages,
funds movement, or production installation occurred. No second scheduler or
pipeline was created.

## Focused verification

- `pytest -q scripts/nexus_agent_platform/tests/test_research_more_followups.py scripts/nexus_agent_platform/tests/test_research_work_queue.py scripts/nexus_agent_platform/tests/test_research_alpha_pipeline.py scripts/nexus_agent_platform/tests/test_research_alpha_lineage.py`
- Result: 18 passed
- Python compilation and `git diff --check`: passed

## Remaining bounded work

Systems, GoClear, and Revenue each require another evidence pass rather than
being forced to qualify. Trading requires a source that exposes concrete,
testable strategy rules before a paper/backtest work order can be justified.
