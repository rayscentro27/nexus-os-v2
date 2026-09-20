# Nexus Overnight Research Morning Audit

Audit basis: canonical runtime `com.nexus.continuous-loop`, execution ledger,
Research queue, Alpha receipts, and governed handoff state. The window begins
at commit `9a6d4365` (`2026-09-20T13:45:09Z`) and ends at the final audit read
(`2026-09-20T14:47Z`, approximate).

## Runtime

| Field | Result |
|---|---|
| `OVERNIGHT_WINDOW` | `2026-09-20T13:45:09Z` → `2026-09-20T14:47Z` (~62 min) |
| `RUNTIME_OWNER` | `com.nexus.continuous-loop` |
| `RUNTIME_UPTIME` | running; PID 42566; launchd owner; 9 runs observed |
| `WAKE_COUNT` | 9 launchd runs; 8 execution IDs in the post-commit ledger |
| `LAST_WAKE` | `2026-09-20T14:44:50Z` execution activity |
| `CURRENT_RUNTIME_STATUS` | `RUNNING` |
| `RUNTIME_CONTINUATION_STATUS` | `PASS_REAL` |

## Actual unattended work

| Metric | Result |
|---|---:|
| `TOTAL_EXECUTIONS` | 8 |
| `WORK_CLAIMED` | 6 claim events; 2 legacy/direct execution records lack claim events |
| `WORK_COMPLETED` | 7 |
| `WORK_RETRYABLE` | 0 new post-commit retryable results |
| `WORK_BLOCKED` | 0 |
| `ACTIVE_LEASES_NOW` | 0 |
| `UNIQUE_OBJECTIVES` | 0 persisted on execution events; objective linkage remains incomplete |
| `UNIQUE_SOURCES` | 5 source URLs |
| `NEW_INFORMATION_ITEMS` | 4 bounded information-bearing results; one result explicitly had no substantive gain |
| `NEW_CLAIMS` | 0 durable claim records attributable to this window |
| `CUSTOMER_SIGNALS` | 0 production customer-demand signals |
| `FOLLOWUP_INVESTIGATIONS` | 4 Alpha `RESEARCH_MORE` follow-ups created |
| `CROSS_SOURCE_INVESTIGATIONS` | 0 completed cross-source investigations in-window |
| `ALPHA_REVIEWS` | 4 evidenced model-backed Alpha reviews |
| `ALPHA_RESEARCH_MORE` | 4 |
| `ALPHA_REREVIEWS` | 0 completed in-window |
| `MARKETING_HANDOFFS` | 0 new unattended handoffs |
| `OTHER_DEPARTMENT_HANDOFFS` | 0 |
| `DUPLICATES_PREVENTED` | 1 unchanged YouTube duplicate skipped |
| `DUPLICATES_PROCESSED` | 0 full duplicate reprocesses in the post-commit records |
| `FAILURES` | 0 post-commit terminal failures |
| `RECOVERIES` | 0 post-commit failure recoveries |

The six claim-backed jobs included WEB and YouTube work. Two post-repair
overlap windows were observed: `research_exec_bc0a881322614fa68bcb` with
`research_exec_7ef39ff84e5e46edb913` (~29 seconds), and
`research_exec_153eaa96bcc046008f03` with
`research_exec_3114d871cdc24b2ab3a4` (~30 seconds). The pairs used distinct
workers/buckets and had no duplicate claims.

## Top unattended findings

1. `research_exec_2065976ef4e241eca6ab`: YouTube metadata/description preserved
   a partial finding about a video on business partners. Evidence status was
   partial; no transcript was available; Alpha was skipped.
2. `research_exec_7ef39ff84e5e46edb913`: a YouTube video discussed credit-union
   offerings and a Navy Federal comparison, but promotions, reviews, and the
   detailed comparison were not extracted. Alpha was skipped.
3. `research_exec_629ff789137f4fc9bc37`: a Reddit post described an $8,500
   janitorial contract; it was anecdotal and lacked formal corroboration.
   Alpha requested more research.
4. `research_exec_463fbb2a3a3547e9bfa3`: a Reddit source relevant to the
   investigation was identified, but the record did not preserve an objective
   ID or durable claim. Alpha requested more research.

The `bc0a...` Reddit execution explicitly reported no substantive evidence;
the `3114...` record was correctly classified as `DUPLICATE_UNCHANGED`.
These results demonstrate processing and bounded partial evidence, not strong
business intelligence.

## Concurrency and retry cleanup

`TOTAL_CONCURRENCY_LIMIT=3`, `YOUTUBE_LIMIT=1`, `WEB_LIMIT=1`,
`DISCOVERY_LIMIT=1`.

`POST_REPAIR_CONCURRENCY_STATUS=PASS_REAL_BOUNDED`: later canonical wakes
showed overlapping WEB and YouTube execution without duplicate claims. The
remaining 13 malformed retries were identified by exact persisted errors
(`unknown url type: ''`) or the deliberate `https://example.test/hackernews`
fixture and transitioned through the existing queue lifecycle to `PARKED`
with `blocker_type=MALFORMED_SOURCE`. No evidence was deleted. Therefore:

- `MALFORMED_RETRIES_BEFORE=13`
- `MALFORMED_RETRY_ACTIONS=park malformed/fixture retries; preserve evidence`
- `MALFORMED_RETRIES_AFTER=0`

The five remaining `FAILED_RETRYABLE` rows are YouTube/provider-specific or
video-specific cases, not malformed URL retries. They remain bounded retry or
fallback work and are not falsely called successful.

## Queue health

Current queue snapshot: `TOTAL_NONTERMINAL=31` (`QUEUED=14`,
`MONITORING=12`, `FAILED_RETRYABLE=5`, `IN_PROGRESS=0`).
`ASSIGNED=31`; `MONITORED=0`, `DEMAND_DISCOVERY=0`, `GENERAL_DISCOVERY=0`
in the current store because historical rows were normalized into ASSIGNED.
`VALID_WORK_AVAILABLE=YES`; `VALID_WORK_CLAIMABLE=YES`; `QUEUED_BUT_UNCLAIMED`
is not evidence of a worker defect while the next wake is pending.

Queue hygiene is still degraded: rows from September 18–19 include legacy
investigations, old Alpha follow-ups, and old certification lineage. The
current Marketing evidence-return item is valid and queued:
`marketing-research-return:mkt_research_return_1ba3a9a0ecc7441583f6`, linked to
`progressive-level-b-objective-20260919` and the existing Research package.

`QUEUE_HEALTH_STATUS=PARTIAL_REAL`: runtime consumption and post-repair
concurrency work, but objective persistence and stale queue hygiene remain
incomplete. `EMPTY_QUEUE_CONTINUATION_READY=PASS_REAL_BOUNDED` based on the
canonical lane scheduler; further wake evidence is still needed for sustained
autonomous demand discovery.

## Morning classification

- `PROCESS_UPTIME=PASS_REAL`
- `PRODUCTIVE_AUTONOMY=PARTIAL_REAL`
- `AI_INVESTIGATION=PASS_REAL_BOUNDED` (plans and interpretations present,
  but several records omit objective linkage)
- `ALPHA_RETURN_LOOP=PARTIAL_REAL` (follow-ups created; no re-review completed
  in this window)
- `CONCURRENCY=PASS_REAL_BOUNDED`
- `QUEUE_HEALTH=PARTIAL_REAL`
- `FAILURE_RECOVERY=PARTIAL_REAL`
- `CUSTOMER_DEMAND_DISCOVERY=FAILED_REAL for this window`
- `DEPARTMENT_HANDOFFS=FAILED_REAL for this window`

`OVERNIGHT_RESEARCH_FINAL_STATUS=PARTIAL_REAL`.
Research is left running independently, but this was not a high-yield
customer-intelligence night.

`RESEARCH_LEFT_RUNNING=YES`
`RAY_REQUIRED_TO_RESTART=NO`
`CODEX_REQUIRED_TO_CONTINUE=NO`

## Evidence paths

- Runtime: `data/runtime/research_execution_jobs.jsonl`
- Queue: `data/runtime/research_work_queue.json`
- AI receipts: `data/runtime/research_ai_orchestration/`
- Marketing return request: governed `research_requests` plus the queue item
  above
- Repair source: `scripts/run_continuous_operating_kernel.py` and
  `scripts/nexus_agent_platform/research_lane_scheduler.py`

