# Nexus Company-Wide Autonomy Failure Audit

## Executive result

The audit found a real continuation failure, not a general scheduler outage.
The control-plane daemons were running and the durable 23-goal portfolio was
present, but the canonical Active Operator had only one generic non-Research
executor: `generate_internal_report`. That action wrote a progress artifact and
updated `last_progress`, but did not satisfy a parent criterion, create a
department implementation action, or make a next-action decision. The two P1
goals consequently monopolized selection and the other goals remained at zero
selection count.

The AI-boundary hypothesis is **partially confirmed**. The observed stop is
after bounded analysis/report creation and before deterministic department
continuation. It is not proven that a model response itself marked every goal
complete; the stronger, evidenced failure is that report/child completion was
treated as sufficient operational progress without a capable next executor.

## Starting state and evidence

- Repository HEAD at audit start: `158fc60f8eaa59cd964eb37ad433f73abe67fd56`.
- The worktree was already substantially dirty; unrelated changes were
  preserved.
- `data/runtime/company_goal_portfolio.json` contained 23 durable goals.
- `trading.real_data` and `research.company_intelligence` each had selection
  count 69; `portal.client_beta`, `portal.admin_control_center`, and the
  other lower-priority goals had selection count 0.
- The active operator receipt at
  `reports/runtime/active_operator_latest.json` contained only
  `generate_internal_report` as the meaningful action. Its result was a local
  report artifact, while `latest_parent_goal_advanced` remained null in the
  continuous-kernel read model.
- The normal continuous kernel was alive, REAL, and self-resuming, but its
  worker state was `IDLE_BETWEEN_CYCLES` between bounded runs.

## Objective reconciliation

| Objective | Current evidence | Stop boundary | Classification |
|---|---|---|---|
| `research.company_intelligence` | Real SearXNG work now produces a persisted result and goal receipt | Alpha/department handoff remains incomplete | `G_ROUTING_FAILURE` before repair; now continuing |
| `trading.real_data` | Existing paper-only OANDA loop produces backtest/OOS/feedback evidence | No proven promotion; next research candidate required | `C_AI_RESPONSE_TERMINATES_FLOW` / repairable continuation |
| `portal.client_beta` | Durable goal exists; existing local portal builders and safety verifier exist | No prior canonical dispatch | `L_OBJECTIVE_NOT_REGISTERED` in the old executor path |
| `portal.admin_control_center` | Durable goal exists; no canonical autonomous executor selected | Admin implementation work not connected | `G_ROUTING_FAILURE` |
| `goclear.example_campaign` | Durable goal exists; internal campaign capability is outside Active Operator | Work order can be queued, not executed by current operator | `B_RUNNING_NO_WORK_SELECTION` |
| `systems.modal_verification` | Capability/provider modules exist | No verified canonical department executor in this loop | `G_ROUTING_FAILURE` |
| `systems.oracle_browser` | Existing bridge/runtime evidence exists | No canonical bounded executor in this loop | `G_ROUTING_FAILURE` |
| Remaining roadmap goals | Durable definitions and dependencies exist | Most lack a safe registered department executor | `J_EXTERNAL_DEPENDENCY` only where evidence says so; otherwise `G_ROUTING_FAILURE` |

No goal was treated as complete merely because a report existed.

## Autonomous loops audited

1. The continuous operating kernel wakes on its normal cadence, writes a
   Research heartbeat, and calls the bounded Research adapter.
2. The Active Operator reads operational state, selects a portfolio goal, and
   creates a canonical work-order record.
3. Before this repair, only `research.refresh` and
   `generate_internal_report` could execute. The latter was used for Trading
   and every unsupported department.
4. The legacy Phase 15 executive portfolio has real product/revenue adapters,
   but it is a separate portfolio/read model and was not the executor behind
   the 23-goal company portfolio. This split is an important architecture
   reconciliation finding; no second scheduler was created.
5. Research/Alpha persistence from commit `158fc60` is a separate, newer
   pipeline and correctly distinguishes durable output from telemetry.

## AI-boundary findings

The generic path was:

`goal selector → next_work_for_active_goal → generic report writer →
record_goal_progress`

`record_goal_progress` intentionally did not mark the parent complete, but it
also did not set a meaningful next action or route the result to an executor.
The selected report was therefore real as a file operation but weak as company
progress. This is the exact post-analysis stop boundary.

The portfolio selector also applied priority before starvation recovery. Since
both P1 goals stayed open, the lower-priority goals were never selected.

## YouTube reconciliation

The current repository does not contain evidence for a durable live batch of
approximately 40 YouTube transcripts.

Recoverable evidence:

- 5 cached YouTube metadata files under `data/cache/youtube/api_metadata/`.
- 5 corresponding yt-dlp metadata files.
- 0 approved transcript files under
  `data/sources/youtube_transcripts/approved/`.
- 1 pending transcript template.
- 1 real-looking manual-loop transcript/artifact for
  `zbAmmnMh5ew` under
  `reports/certification/manual_loops/20260827T095143/`; this is not proof of
  a live autonomous batch.
- NotebookLM export memory contains 161 source records and 60 opportunity
  records in a report/export pipeline, but the current evidence does not map
  those records to 40 YouTube videos or to the canonical current Research →
  Alpha lineage.

Therefore the defensible counts are:

- recoverable YouTube metadata records: 5;
- approved transcript corpus: 0;
- recoverable transcript artifact: 1;
- current live YouTube scheduler proof: not proven;
- current canonical Alpha evaluations for that historical batch: not proven.

The old audit explicitly says the UI/Alpha/Hermes YouTube flow was not
connected. Cached metadata and NotebookLM exports must not be represented as
durable current company knowledge until imported through the canonical
Research/Alpha store. Useful source knowledge should be preserved separately
from opportunity scores; the current evidence does not prove that this
separation existed for the historical batch.

## Alpha reconciliation

The current canonical lineage query has shown one persisted Research item with
an Alpha evaluation (`REJECTED`, score 0) and no downstream route. The latest
bounded Alpha heartbeat showed zero new candidates and zero new evaluations.
That is truthful for the current canonical store; it is not proof that the
historical YouTube exports were evaluated there.

The trading loop demonstrates the desired non-terminal behavior: its rejected
OOS candidate persisted a critique, learning record, and a
`RESEARCH_AND_RETEST` feedback work order. This is a valid continuation
pattern. It should be generalized to Research/Alpha inputs rather than using a
rejection as mission termination.

## Portal reconciliation

The durable portfolio contains both portal goals, but the old Active Operator
did not route them to portal capability. Existing safe local capabilities are
present:

- `scripts/client_flow/run_client_portal_backend_build.py`;
- `scripts/client_flow/verify_client_portal_safety.py`;
- existing local/demo portal exports and admin review queue builders.

No evidence supports autonomous production deployment or customer mutation.
Those remain governed. Local build, audit, test, and receipt work are not
human-only, and were previously stranded by the missing generic route.

## Safety

The repair preserves the paper-only trading boundary. No live trading,
customer communication, publication, payment, grant submission, production
database mutation, or external outreach was performed.

## Conclusion

The company OS was live as infrastructure but not yet complete as a goal
completion engine. The missing boundary was deterministic continuation and
capability-aware routing after a child action. The companion repair report
records the code change and bounded live proof.
