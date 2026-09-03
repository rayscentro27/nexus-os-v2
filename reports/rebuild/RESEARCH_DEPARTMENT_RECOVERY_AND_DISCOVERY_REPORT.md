# Research Department Recovery and Discovery Report

## Executive Result

The canonical Alpha research path is operational for bounded, public, read-only
work. A fresh run completed one approved YouTube transcript retrieval and one
public website retrieval, persisted both with source hashes, created claims and
an internally governed capability-improvement work order, and a subsequent
identical discovery reused the existing records without creating duplicates.

Ray's assigned YouTube set is only partially complete: four approved channels
and one approved video are identified; metadata was obtained for all five
targets, while transcript/research completion is proven for one approved video.
The Research launchd worker is not loaded, so overnight autonomous readiness is
not certified. This is an operational scheduler/deployment gap, not a Ray-only
blocker.

## Prior Ray Assignment Reconciliation

The durable assignment source is `configs/youtube_research_channels.json` plus
the watched-resource report. It identifies four approved channels (Credit Plug,
Michael Ionita, Alec Delpuech, and Stedman Waiters) and one approved video
(`zbAmmnMh5ew`). Existing Alpha records also contain historical URL research
objectives; they were retained and reconciled rather than duplicated.

The bounded reconciliation object is the operational-state projection in
`scripts/nexus_agent_platform/research_operational_state.py`. It projects the
append-only canonical records and latest logical queue state; it is not a new
queue or source-of-truth store.

## YouTube Assignment

| Measure | Result |
|---|---:|
| Channels identified | 4 |
| Approved targets | 5 |
| Videos discovered/metadata processed | 5 unique targets |
| Transcripts obtained | 1 |
| Transcript failures/unavailable subtitle targets | 4 remaining targets had no available subtitle result in the bounded probe |
| Research completed | 1 bounded Alpha research objective |
| Remaining | 4 approved channel/video targets need governed transcript/research continuation |

Evidence: the real `run_youtube_ytdlp_probe.py --approved-only --no-download`
run inspected five approved targets without media/audio download. The subsequent
Alpha run produced research `research_1204f3af106e9f8138b5`, content and claim
records, and a real transcript hash for `zbAmmnMh5ew`. No media was downloaded.

## Website Assignment

Ray's durable assignment list does not preserve an unambiguous website owner
field. One identifiable public website source in the current research evidence,
`https://www.consumerfinance.gov/`, was processed in the fresh bounded Alpha
run. Retrieval succeeded through the governed public-read fallback, with title,
content hash, excerpt, timestamp, and source reference persisted.

| Measure | Result |
|---|---:|
| Identifiable website sources | 1 |
| Pages processed | 1 |
| Research completed | 1 bounded page review |
| Remaining | 0 for this bounded website test; historical assignment attribution remains partial |

## Remaining Work

Four approved YouTube targets remain without proven transcript/research output.
The existing source policy permits metadata/manual transcript handling and does
not authorize media downloads. A durable continuation is therefore required for
those targets; the parent-objective projection keeps them open when sources
remain.

## Repaired Blockers

The operational-state projection now separates latest queue state from historical
append-only rows. It explicitly reports department state, Alpha activity,
specialist availability, background process state, work state, health,
readiness, counts, parent-objective progress, and the next action when the queue
is empty. Alpha executive status now uses this projection, preventing “idle” or
an old heartbeat from being reported as “inactive.”

## Resumed Work

A fresh bounded batch was run through the existing Alpha worker path:

* approved YouTube video `zbAmmnMh5ew` → real transcript retrieval;
* CFPB public page → real HTML retrieval and extraction;
* source hashes, claims, research result, and governed routing were persisted;
* capability-improvement work order `wo_562c0850a36b33e85826` was present for
  the bounded YouTube/website objective.

The autonomous discovery batch used three current public sources (MCP
specification, Anthropic MCP announcement, and Python public homepage), created
research `research_d706404c3363d477836d`, three content records, three claims,
and work order `wo_580189405b68f88d888e`. No external action was performed.

## Department Operational State Contract

The reusable contract is represented in
`nexus_agent_platform.research_operational_state` and preserves these
invariants: `IDLE != UNAVAILABLE`, `AVAILABLE != ACTIVE`, `QUEUE_EMPTY !=
UNAVAILABLE`, and one failed worker does not imply department failure.
Append-only queue records are reduced to their latest logical state before
counts are reported.

## Current Alpha / Research State

Current projection at report time:

* `RESEARCH_DEPARTMENT_OPERATIONAL_STATE=OPERATIONAL`
* `ALPHA_PRIMARY_AGENT_ACTIVITY=IDLE`
* `ALPHA_SPECIALIST_AVAILABILITY=AVAILABLE`
* `RESEARCH_BACKGROUND_PROCESS_STATE=STOPPED`
* `RESEARCH_WORK_STATE=NO_CURRENT_WORK`
* `RESEARCH_HEALTH=HEALTHY`
* `RESEARCH_EFFECTIVE_READINESS=READY_DEGRADED`
* `ACTIVE_RESEARCH_JOBS=0`
* `QUEUED_RESEARCH_JOBS=0` (latest queue state)
* `BLOCKED_RESEARCH_JOBS=0`
* `OPEN_RESEARCH_OBJECTIVES=14` (historical canonical Alpha objectives)
* latest successful activity `2026-09-03T02:14:34Z`
* `RESEARCH_NEEDS_RAY=NO`

Alpha availability is derived from the canonical specialist/status evidence;
worker activity is reported separately. The old research launchd plist exists,
but `launchctl print` shows no loaded `com.nexus.research-worker` service.

## YouTube Research Proof

`DEGRADED_REAL`: metadata discovery ran against all five approved targets with
no download. One approved video then completed real subtitle retrieval through
the existing Alpha path; four remaining targets did not yield subtitles in the
bounded probe. No transcript was fabricated.

## Website Research Proof

`PASS_REAL` for the bounded CFPB test: URL accepted, public content retrieved,
text extracted, SHA-256 source hash recorded, claim/research rows persisted, and
the result routed for governed internal review.

## Knowledge Pipeline

The Alpha path persisted `alpha_content`, `alpha_claims`, and `alpha_research`
records, then routed qualified findings to governed `work_orders` and
`alpha_outcomes`. The bounded autonomous finding was marked for Nexus capability
improvement/review; it was not auto-approved or published.

`RESEARCH_RESULTS_PERSISTED=PASS_REAL`
`PROPOSED_KNOWLEDGE_GENERATION=PASS_REAL`
`SOURCE_TRACEABILITY=PASS_REAL`

## Knowledge Reuse

The exact autonomous-discovery request was run twice after its first persisted
result. Both runs returned the same research ID and the second run produced zero
delta in content, claim, or research row counts. This proves the existing
content/research identity checks suppress duplicate research for that bounded
case.

`KNOWLEDGE_REUSE=PASS_REAL`
`DUPLICATE_RESEARCH_SUPPRESSION=PASS_REAL`

## Autonomous Discovery

`PASS_REAL`: a fresh objective-driven request evaluated three public sources
relevant to Nexus MCP and bounded agent operations. It produced three source
references, three claims, novelty-aware content identities, a challenged result,
and a governed internal capability-improvement route. No random browsing,
external publishing, or third-party installation occurred.

`NEW_INFORMATION_FOUND=YES` at first discovery; the subsequent identical run
confirmed reuse rather than duplicate ingestion. `NOVELTY_CHECK=PASS_REAL`.

## Research → Next Work

`PASS_REAL`: the fresh autonomous result was evaluated and routed to
`nexus_capability_improvement`, with governed work order
`wo_580189405b68f88d888e` and Alpha ownership. It remains a candidate/review
state and is not treated as approved implementation.

## Empty Queue Behavior

The operational contract emits
`INSPECT_INCOMPLETE_OBJECTIVES_AND_CONTINUE` when the queue is empty but parent
objectives exist; otherwise it selects bounded autonomous discovery when the
research path is healthy, or explicitly reports no high-value cycle. The current
projection selected the first action because incomplete historical objectives
remain. This prevents an empty queue from being interpreted as “nothing to do.”

## Tonight Readiness

Research is operational for bounded invocation but is not certified ready for an
overnight autonomous loop because the canonical research-worker launchd service
is not loaded. The existing plist points at a legacy external `nexus-ai` worker
path and was not activated or rewritten in this package. Activating that
unverified service would broaden scope and could create duplicate workers.

## Safety

All live work was public, bounded, read-only research. No client PII, secrets,
external publishing, purchases, financial transactions, or live trading were
performed. Existing duplicate protection and approval-required routing were
preserved.

## Tests

* Focused Research/Alpha regressions: **41 passed**.
* The broader contracts module could not collect because the environment lacks
  the unrelated `temporalio` package; no dependency was installed.
* Real bounded YouTube metadata/transcript and website Alpha tests: passed as
  described above.
* Autonomous discovery and exact-repeat knowledge-reuse test: passed.
* Canonical build: **PASS_EXIT_0** (`npm run build`; Tailwind, TypeScript, and
  Vite completed).
* Secret scan: **PASS**; targeted secret-pattern scan over task code/report
  outputs found no credential-shaped values, and no secrets were printed.

## Git

Unrelated existing worktree changes were preserved and no broad staging or
cleanup was performed. Only the operational-state implementation, Alpha status
integration, focused tests, and this report are task outputs; generated runtime
artifacts and pre-existing dirty files remain unstaged.

## Final Status

`RESEARCH_PHASE=PARTIAL`: bounded web/YouTube research, persistence, reuse,
discovery, and routing are real and operationally legible. Full assignment
completion and overnight readiness remain open pending governed scheduler
activation/ownership and continuation of the four remaining approved YouTube
targets.

`TRUE_RAY_BLOCKERS=NONE`.

`NEXT_RECOMMENDED_PHASE=GOAL_COMPLETION_ENGINE`: activate/repair the canonical
Research scheduler under an explicit single-owner deployment change, then run
the remaining approved YouTube continuation batches and re-certify overnight
readiness.
