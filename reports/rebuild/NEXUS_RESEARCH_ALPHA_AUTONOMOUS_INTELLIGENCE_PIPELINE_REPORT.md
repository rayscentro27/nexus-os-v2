# Nexus Research → Alpha Autonomous Intelligence Pipeline

## Executive result

The first telemetry discrepancy was not a Nova formatting problem. The
`2 new items` count came from the Alpha source-monitoring heartbeat at
`2026-09-05T03:00:26.974673Z`; its two content/claim records were durable, but
they were before Phoenix midnight for the later Telegram query. The 09:01Z
continuous-kernel cycle repeated an existing internal Research candidate and
did not create those two items.

The deeper production gaps were real:

1. Alpha source persistence did not expose a formal item-level Research-output
   contract.
2. Alpha intake had no durable scored-evaluation store.
3. Source identity deduplication allowed a changed title for the same URL to
   inflate the `new` counter.
4. One scan could evaluate the same item twice because the in-memory claimed
   set was not updated after the first append.

These are repaired without changing Nova, the model, the scheduler, or the
external-action boundary.

## Prior counter truth

The two records behind the prior counter were:

| Item | Artifact / claim | Source | Research chain |
|---|---|---|---|
| The End of Paid Software? 10 Repos You Need to Know | `content_3b6e95bbf8d969257d66`, claim `claim_84ce2a0b40dd04b146f7` | `https://www.youtube.com/watch?v=o_YngNoGP1I` | `research_56ac934d2ed668056bcb` |
| Watch Me Scale This $13K/Month Coach To $50K (Live Breakdown) | `content_512a3164324c23f59fcc`, claim `claim_4ceb8cea101bd65b57ce` | `https://www.youtube.com/watch?v=N95roD3fcFg` | `research_56ac934d2ed668056bcb` |

Both were persisted as source observations with `UNVERIFIED` verification and
no supported evidence. The original Alpha state was `CHALLENGED` intake plus a
Growth candidate handoff; it had no score, evaluation ID, or evaluation
reasoning. This explains why the repaired lineage query correctly reported no
Alpha scores for that historical window.

## Current live truth

At the final live verification, the Phoenix-day query window was:

```text
2026-09-05T07:00:00Z → current
```

It returned one canonical current-day item after deduplicating the repeated
URL identity:

```text
research_item_id = content_3b6e95bbf8d969257d66
title            = 10 GitHub Repos That Will Kill Every Subscription You Still Pay For
research_id      = research_1b8bb81332647486e656
alpha_eval_id    = alpha_eval_549c396690644aa3bfd3f869bfe11ffa
score            = 0
decision         = REJECTED
reason           = The persisted evidence is unverified or too weak for downstream qualification; retain it as research evidence and do not create department work.
route            = NONE
status           = REJECTED
```

The score is a deterministic Alpha evidence score derived from the persisted
claim's existing `evidence_score=0.0`; it is not a profitability or business
value claim. No downstream work order was created for the rejected item.

## Architecture repair

Added `scripts/nexus_agent_platform/research_alpha_pipeline.py`.

It reuses the governed append-only persistence layer and provides:

```text
persisted alpha_content / alpha_claims
        ↓
exactly-once Alpha intake by research_item_id
        ↓
alpha_evaluations.jsonl
        ↓
existing route_finding only for QUALIFIED items
```

The evaluation schema records evaluation ID, Research item ID, content and
Research IDs, score, decision, reasoning, confidence, dimensions, timestamp,
next route, and status. Weak or rejected items remain observable and do not
create downstream work.

`alpha_content` now records the Research-output fields on new writes:
Research item ID, objective, finding, verification state, confidence, Alpha
eligibility, lifecycle status, and creation time. The existing Alpha content
store remains the canonical source artifact store; no competing database was
created.

`persist_content()` now treats canonical `content_id` as the identity even if a
source title/excerpt changes. This prevents a source refresh from being counted
as a new intelligence item. The pipeline also updates its claimed set after
each append, preventing duplicate evaluations in one cycle and across restarts.

## Counter integrity

The heartbeat now distinguishes:

- `sources_checked`;
- `candidates_seen`;
- `candidates_rejected`;
- `new_persisted_items`;
- `alpha_evaluations_created`.

`new_items_discovered` remains compatible as an alias for the durable count,
not a transient source delta. The final real Alpha heartbeat reported:

```text
sources_checked=3
candidates_seen=0
candidates_rejected=0
new_persisted_items=0
new_items_discovered=0
alpha_evaluations_created=0
```

It remained self-resuming and continued to write the normal activity state.

## Autonomous cycle proof

Normal continuous supervisor path:

```text
cycle_id       = kernel_cycle_1
started        = 2026-09-05T13:50:20.044143Z
completed      = 2026-09-05T13:50:28.956845Z
status         = PASS
execution_mode = REAL
department     = Research
action         = generate_internal_report
external       = false
next_action    = CONTINUE_INCOMPLETE_OBJECTIVE
```

The normal Alpha/Research heartbeat then executed a real bounded public-source
read at `2026-09-05T13:50:36.408008Z`. No fake record was injected. Existing
persisted evidence was evaluated through the same governed pipeline, and the
next run produced zero new items and zero new evaluations after idempotency
was verified.

## Restart and duplicate safety

The governed collection `alpha_evaluations` is append-only and reloadable.
The evaluator checks persisted Research item IDs before evaluation, and the
content writer checks canonical content IDs before persistence. Focused tests
cover duplicate Research cycles, duplicate Alpha intake, reload persistence,
rejected candidates, and lineage visibility.

## Tests

```text
38 passed — focused Research/Alpha pipeline, lineage, heartbeat, kernel,
             Research-state, Alpha discovery, and Nova grounding tests
```

The existing relevant regression suites remain green. The original lineage
projection tests also continue to pass.

## Nova visibility

Nova reads the same canonical lineage projection from:

`scripts/nexus_agent_platform/research_alpha_lineage.py`

It now exposes actual persisted output, artifact identity, Alpha evaluation,
decision/reason, route, and status. It does not substitute heartbeat counters.

## Remaining limitation

The earlier two source observations remain rejected/unverified; no qualified
downstream work is claimed. That is a valid evidence result, not a fabricated
success. Future cycles remain enabled for monitored sources, Research
objectives, verification, stale knowledge, and department needs.

## Ray certification boundary

Repository/runtime proof is complete. A fresh Ray-originated Telegram message
is still required to certify the live executive surface. Send:

> What did Research produce since midnight, what did Alpha score, and what happened to each item?

The expected response must contain the persisted item and score/decision above,
not heartbeat-only telemetry.

## Git

Base: `697c58310b6b23bfc2d44cd65bd8c73e80737270`.

Task changes are limited to the governed evaluation collection, pipeline,
heartbeat/continuous discovery integration, deduplication repair, tests, and
this report. Unrelated worktree changes were preserved and unstaged.
