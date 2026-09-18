# Nexus Research Overnight / Yesterday Productivity and Handoff Audit

Audit snapshot: 2026-09-18 07:32 Phoenix time.

## Scope and time windows

- Timezone: `America/Phoenix` (MST, UTC-07:00).
- Yesterday: `2026-09-17 00:00:00 -07:00` through `2026-09-17 23:59:59 -07:00` (`2026-09-17T07:00:00Z` through `2026-09-18T06:59:59Z`).
- Overnight: `2026-09-17 18:00:00 -07:00` through the audit snapshot, `2026-09-18 07:32:09 -07:00` (`2026-09-18T01:00:00Z` through `2026-09-18T14:32:09Z`).
- Overnight is deliberately an evening-to-current-morning window, not a rolling 24-hour interval. It overlaps the last six hours of the yesterday window.

## Evidence used

The audit cross-checked:

- `data/runtime/research_execution_jobs.jsonl` for execution lifecycle events, source selection, terminal dispositions, and retries.
- `data/governed/research_v2_sources.jsonl`, `research_v2_claims.jsonl`, `research_v2_comparisons.jsonl`, `research_v2_investigations.jsonl`, `research_v2_questions.jsonl`, `research_v2_missions.jsonl`, `research_v2_mission_items.jsonl`, `research_v2_mission_reports.jsonl`, `research_v2_alpha_reviews.jsonl`, `research_v2_handoffs.jsonl`, `research_v2_plans.jsonl`, `research_v2_strategies.jsonl`, `research_v2_opportunities.jsonl`, `work_orders.jsonl`, and `research_requests.jsonl`.
- `data/runtime/research_heartbeat.json` and `research_operational_state.py` for current health, continuation, queue, and objective projection.
- `data/runtime/alpha_research/*.json` and receipt files for actual Alpha review executions.
- `reports/runtime/research_artifacts/` for persisted evidence/provenance artifacts.
- `data/runtime/nexus_mcp_receipts/` and department receipt directories for handoff/department execution evidence.
- Current mission and handoff records, not the legacy Alpha “completed missions” counter.

The repository contains a large amount of older report material. Reports whose timestamps were outside these windows were used only for historical context and were not counted as current productivity.

## Measured activity

`research_execution_jobs.jsonl` contains one lifecycle sequence per execution. A run is counted once by `execution_id`, not once per lifecycle event.

| Measure | Yesterday | Overnight |
|---|---:|---:|
| Research runs / execution IDs | 88 | 41 |
| Unique source IDs selected | 15 | 10 |
| Fully processed terminal outputs | 48 | 27 |
| Explicit `DUPLICATE_UNCHANGED` outputs | 27 | 9 |
| Failed/retryable runs | 11 | 5 |
| Incomplete/no terminal disposition | 2 | 0 |
| V2 investigation records touched | 10 | 1 |
| V2 claim records | 25 | 0 |
| V2 comparison records | 9 | 1 |

The 48 and 27 fully processed events are processing outputs, not 75 or 27 proven new findings. Many repeated the same source, and the persisted comparison records explicitly use qualitative novelty rather than a numeric novelty score.

## Productivity versus activity

The observed execution-level productive rate, using `FULLY_PROCESSED` as the broadest measurable productive disposition, was:

- Yesterday: `48 / 88 = 54.5%`.
- Overnight: `27 / 41 = 65.9%`.

That broad rate overstates business productivity. In the same data, 27 yesterday and 9 overnight runs were explicitly unchanged duplicates. The source-selection distribution shows repeated processing of `hubspot-affiliate`, `google-seo-starter`, `reddit-smallbusiness`, `sba-business-guide`, `shopify-partners`, `sba-grants`, and `sushantkarn/SEO-engine`. Several sources were processed repeatedly while their outputs remained unchanged.

Conservative classification:

- `PRODUCTIVE_NEW_FINDING`: 9 yesterday / 1 overnight comparison records marked `ADDS_NEW_INFORMATION`; these are evidence additions, not automatically qualified business findings.
- `USEFUL_FOLLOWUP`: 1 overnight V2 investigation evidence attachment, plus current Alpha review executions against existing findings.
- `EVIDENCE_REFRESH`: the remaining successful processing events where a source was processed but no durable new decision or qualified finding was created.
- `DUPLICATE`: 27 yesterday / 9 overnight explicit unchanged dispositions, plus repeated successful processing of the same source IDs.
- `FAILED`: 11 yesterday / 5 overnight retryable or non-completed executions.
- `NO_VALUE_CYCLES`: at least 27 yesterday / 9 overnight explicit unchanged cycles; the true count may be higher because some `FULLY_PROCESSED` cycles contain extraction refreshes without a new governed decision.

No evidence supports calling the overnight period a high-value autonomous research shift. It was active and mostly successful at source processing, but it remained repetitive and did not produce corresponding Alpha qualification or department execution.

## What Research actually worked on

Meaningful source families and their observed disposition:

| Source / topic | Window evidence | Assessment | Next action |
|---|---|---|---|
| HubSpot affiliate program | Repeated selection; multiple `FULLY_PROCESSED` outputs | Preliminary affiliate/program intelligence; source extraction is noisy and still needs independent evidence | Verify terms, economics, eligibility, and measurement before any offer or content action |
| Google Search Central SEO Starter | Repeated selection; official documentation processed | Useful baseline SEO guidance, not a Nexus-specific opportunity by itself | Convert only into a bounded SEO test with a target page and measurement plan |
| Mobile detailing Phoenix | Source artifact and comparison persisted; opportunity remains `THESIS_ONLY_NO_EXECUTION` | Potential local business hypothesis; claims are from a commercial guide and require independent validation | Validate demand, pricing, regulation, and customer acquisition with independent sources |
| Shopify partner ecosystem | New comparison and claim extraction | Potential affiliate/partner pathway, but payout and program claims are not independently qualified | Verify current partner terms and model economics |
| Investor/investing basics and SBA sources | Evidence attachments and comparisons | Reference material, mostly `RESEARCH_MORE`; not a completed recommendation | Select independent authoritative evidence for open gaps |
| Recovered YouTube mission | Three items already completed and Stedman Waiters externally blocked | Mission reached `PARTIAL`; it did not create a new 20-channel result | Keep blocked item out of normal rotation until an approved acquisition path changes |
| GitHub/SEO and other repeated sources | Repeated source selection, many unchanged results | Repetition rather than new intelligence | Improve novelty/age gating before reprocessing |

The current operational reader reports Research `HEALTHY`, `READY`, background process `ACTIVE`, `WORKING_V2_INVESTIGATIONS`, zero active/queued/blocked jobs at the snapshot, and `open_research_objectives=90` from the legacy Alpha ledger. That 90-objective projection must not be interpreted as 90 current productive investigations.

## Finding quality

No finding in the audited period can be classified as `STRONG` on the available evidence. The safest quality counts are:

- `STRONG_FINDINGS_COUNT=0`.
- `USEFUL_FINDINGS_COUNT=2` at preliminary/hypothesis level: the Phoenix mobile-detailing opportunity and the affiliate content-to-commission thesis. Both remain unvalidated and require bounded tests.
- `WEAK_FINDINGS_COUNT=at least 7` source-extraction/comparison outputs whose evidence is generic, noisy, commercial, or insufficiently corroborated for a business decision.
- `STALE_FINDINGS_COUNT=0` for newly written records, but repeated unchanged processing is a freshness/productivity problem. Existing stale material was not counted as new output.

The clearest persisted business thesis is the affiliate content-to-commission method. Its plan says the mechanism is unknown until tested, with missing rules around sample size, timing, costs, and failure criteria. That is a useful test candidate, not revenue proof.

## Alpha review and handoff audit

`data/governed/research_v2_alpha_reviews.jsonl` has no records written in either requested window. `data/governed/research_v2_handoffs.jsonl`, plans, and strategies also have no new records in either window.

There are six distinct Alpha runtime review jobs in the overnight/current-morning receipt set. They all used the same objective (“Review the most recent Research finding…”), completed locally, and had `model_calls=0`. The available packs carried four distinct evidence references; those sources reported `freshness=UNKNOWN` and `quality=UNVERIFIED`. Therefore:

- `TOTAL_ALPHA_REVIEWED=6` runtime review executions, `4` distinct evidence references.
- `TOTAL_ALPHA_QUALIFIED=0` decision-grade qualified findings.
- `TOTAL_ALPHA_MORE_RESEARCH_REQUIRED=6` (the review evidence was not fresh/verified enough to qualify an action).
- `TOTAL_MISSING_ALPHA_HANDOFFS=2` material thesis-level items that remained in draft/review-required state without a new governed Alpha review/handoff in this window.

No new department handoff was created during the window. Existing handoffs include draft review requirements for the mobile-detailing plan and affiliate bounded test. No new work order was created from those findings. Work orders created by recovery checks were not Research handoffs and were excluded.

## Mission and investigation semantics

The V2 mission ledger and the legacy Alpha mission ledger have different meanings. The legacy Alpha ledger’s historical completed count is not used as a current bounded-mission count.

- Bounded V2 mission started/touched yesterday: `1` recovered YouTube mission.
- Bounded V2 mission completed: `0` fully completed; `1` became `PARTIAL`.
- Bounded V2 mission externally blocked: `1` item, Stedman Waiters, with `BLOCKED_EXTERNAL_FINAL`.
- Mission items already completed: `3`, but their records describe already-completed channels rather than new work in this window.
- Overnight bounded missions started: `0`; the overnight source-processing work was Research V2 source rotation, not a new bounded mission.

The current operational projection reports `40` open V2 investigations. The append-only investigation ledger contains `37` distinct investigation IDs after latest-record reduction; the discrepancy is a projection/ledger semantic difference and should not be collapsed into a single “40 completed” claim. Ten investigations advanced yesterday and one additional investigation advanced during the overnight/current-morning segment; approximately 30 current projected investigations had no measured advance yesterday and 39 had no advance in the overnight segment.

## Autonomy and scheduler effectiveness

Overnight autonomy is real at the process/continuation level:

- `research_heartbeat.json`: active daemon, `execution_mode=REAL`, `resume_without_manual_restart=true`, `queue_empty_does_not_stop=true`, `objective_has_durable_owner=true`, and a current next wake.
- The current cycle selected `AFFILIATE_REVENUE`, dispatched work, and reached `EVIDENCE_READY`/`COMPLETED` for the HubSpot source.
- No manual restart was required in the observed window.
- No unexpected stop was observed.

Productivity is weaker than uptime:

- Scheduler wakeups/execution cycles observed: `88` yesterday and `41` overnight.
- Wakeups with broad productive processing: `48` yesterday and `27` overnight.
- Broad productive wake rate: `54.5%` yesterday and `65.9%` overnight.
- Wakeups with explicit no-change duplicate work: `27` yesterday and `9` overnight.

Thus `OVERNIGHT_AUTONOMY=PASS_PROCESS_CONTINUATION_BUT_LOW_BUSINESS_THROUGHPUT`. The daemon continued without intervention, but the evidence does not show that autonomous continuation reliably selected the highest-value next work.

## Stuck items and missed opportunities

1. Affiliate content-to-commission thesis: current stage `DRAFT_REVIEW_REQUIRED`; expected next stage is bounded test design and approval. It is stuck on missing independent evidence, test rules, measurement, and approval boundary (`WEAK_EVIDENCE` / `APPROVAL_REQUIRED`).
2. Phoenix mobile-detailing opportunity: current stage `THESIS_ONLY_NO_EXECUTION`; expected next stage is independent validation and a bounded no-spend test. It is stuck on unverified market/pricing assumptions (`WEAK_EVIDENCE`).
3. Stedman Waiters: current stage `BLOCKED_EXTERNAL_FINAL`; expected next stage is approved media/transcript acquisition. It is correctly blocked by external acquisition limits, not by an internal missing handoff.
4. Repeated source rotation: current stage is repeated `FULLY_PROCESSED` or `DUPLICATE_UNCHANGED`; expected next stage is novelty/age-aware suppression or a deliberately selected independent source. This is a pipeline prioritization issue, not a source-availability issue.

Missed handoffs: two thesis-level items remained in draft review state. Missed Alpha reviews: the governed V2 review ledger has zero new reviews for the period, despite six runtime review packs. Missed tests: no bounded business test or department execution was recorded from the two useful thesis-level findings. Missed department actions: zero new Research-to-department work orders in the period.

## Business value

No realized revenue, affiliate conversion, validated offer, cost saving, or completed department action is evidenced for the period. Potential business-value outputs were:

- `AFFILIATE_OPPORTUNITY`: affiliate content-to-commission mechanism; evidence level `UNVERIFIED / PRELIMINARY`; next test is a reviewed, disclosure-compliant, no-spend bounded content/measurement experiment.
- `BUSINESS_OPPORTUNITY`: Phoenix mobile detailing; evidence level `THESIS_ONLY_NO_EXECUTION`; next test is independent local demand/pricing/regulatory validation.
- `SEO/PRODUCT_IMPROVEMENT`: Google SEO guidance and repository/tooling sources; evidence level `BASELINE`; next test requires a concrete owned-page experiment.

No revenue estimate is justified by the records.

## Cost telemetry

Research execution and Alpha receipt records do not contain complete provider token/cost telemetry for the window. Alpha review packs explicitly report `model_calls=0`; Research job records do not provide a trustworthy per-run token/cost field. Therefore:

- `MODEL_CALLS=UNAVAILABLE_FOR_RESEARCH_LEDGER`.
- `PROVIDER=UNAVAILABLE_FOR_RESEARCH_LEDGER`.
- `MODELS_USED=UNAVAILABLE_FOR_RESEARCH_LEDGER`.
- `TOKEN_USAGE=UNAVAILABLE`.
- `ESTIMATED_COST=UNAVAILABLE`.

## Recommended next machine-selected work

1. Stop reprocessing unchanged sources until a new-evidence or age threshold is met.
2. Advance the affiliate thesis only through an independent evidence check and a bounded, approval-gated measurement brief.
3. Advance the Phoenix mobile-detailing thesis only through independent demand/pricing/regulatory evidence; do not publish or spend.
4. Keep Stedman Waiters excluded from normal rotation until an approved transcript/media path becomes available.
5. Select the oldest high-materiality `RESEARCH_MORE` investigation with a concrete independent source, then require a governed Alpha review before any department handoff.
6. Close or explicitly park screened/empty legacy objectives instead of allowing the legacy 90-objective projection to drive repeated rotation.

## Final classification

This audit is `PASS_REAL` as an evidence audit, not a claim that Research generated high business value. The key conclusion is: Research stayed alive and processed real sources, but overnight output was mostly repeated source processing, with no new governed Alpha qualification or department handoff. The two best candidates remain preliminary hypotheses awaiting evidence and approval.

