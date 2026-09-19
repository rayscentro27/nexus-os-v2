# Nexus Research Productivity Correction — 2026-09-19

## Result

The overnight runtime was alive and completed source work, but company-value
throughput was low. The audit inspected 112 completed executions in the exact
persisted window from `2026-09-18T23:09:33.015771+00:00` through
`2026-09-19T13:13:39.678200+00:00`. The prior aggregate ledger reported 115
terminal completions; three were outside the inspected completion-event slice.

Of the inspected executions, 66 were new fully processed outputs and 46 were
unchanged duplicates. All 112 emitted an evidence-ready event, but all 112
carried `alpha_status=NOT_INVOKED`. This is the principal value leak: storage
success was being counted without downstream evaluation.

## Drop-off diagnosis

| Boundary | Evidence | Cause |
| --- | ---: | --- |
| source → Research | 112/112 completed sample reached the router | 16 other jobs failed retryably: 13 scheduled processor failures and 3 source-selection failures |
| Research → evidence | 112/112 emitted evidence-ready; 66 new extractions | duplicate/unchanged sources correctly suppressed, but monitoring dominated the cycle mix |
| evidence → Alpha | 0/66 overnight eligible outputs invoked Alpha | Alpha was only called by the no-lane fallback and the legacy `alpha_content` path; the V2 scheduled worker stamped assigned outputs as `NOT_INVOKED` |
| Alpha → department | 0 overnight handoffs | no model-backed Alpha decision was made for those outputs |
| department → result | no new overnight Research-v2 result for this cohort | no handoff entered the department consumer |

Calculated rates for the inspected completed sample:

- useful new output: `66/112 = 58.9%`
- duplicate output: `46/112 = 41.1%`
- monitoring disposition: `65/112 = 58.0%`
- evidence-ready: `112/112 = 100%`
- Alpha eligible new outputs: `66/112 = 58.9%`
- Alpha invocation on eligible overnight outputs: `0/66 = 0%`
- handoff eligible/executed in this cohort: `0/0`

These metrics do not treat a heartbeat, queue inspection, or duplicate check as
business productivity.

## Repairs made

1. Added `review_assigned_research_output()` to the existing
   `research_alpha_pipeline`. It consumes only completed assigned or bounded
   demand-discovery outputs, uses the existing model-backed Alpha review and
   receipt contract, is idempotent on the source identity, and does not create
   a second queue.
2. Connected the existing dispatched Research worker to that bridge after
   evidence persistence. Routine monitoring and unchanged duplicates remain
   cheap and are not sent to model review.
3. Fixed the existing Alpha follow-up serialization defect. A list of source
   URLs was being placed in scalar `source_url`; follow-up workers therefore
   received unusable input. The first governed source URL is now preserved and
   the candidate list remains in `source_candidates`.
4. Repaired the already-created CRJ follow-up queue item in place and ran it
   through the existing Research worker. No new queue or scheduler was added.

## CRJ continuation evidence

The four bounded CRJ candidates completed through the existing Research path:

- `crj-home` → `package_3a72678b46c54f8469de`
- `crj-automation` → `package_acbe0a7c18e4f9d98282`
- `crj-support-outsourcing` → `package_f2fbd4fe453e71004e19`
- `crj-support` → `package_6c0015c53db9cf51eb47`

The combined public evidence package received a real Alpha review:

- receipt: `alpha_receipt_a3db4882e2dd4ee9b413a2c0acc3b89f`
- decision: `RESEARCH_MORE`
- follow-up: pricing structure, trial terms, customer service, and specific
  integrations remain insufficiently evidenced
- no vendor activation or external action was taken

The existing follow-up then completed through Research as
`package_feabb80908934e5e3455`. The parent CRJ objective remains `WAITING`
because the evidence loop is intentionally open; it is not falsely marked
complete. Alpha's existing consumer now has a valid scalar URL for subsequent
follow-up work.

## Productivity policy correction

The existing work-selection system remains authoritative. Its effective
ordering is now documented and enforced at the handoff boundary:

1. assigned objectives and Alpha follow-ups;
2. department requests and bounded company-objective work;
3. customer-demand discovery and evidence development;
4. Clyde/funding and monetization questions;
5. SEO and capability discovery;
6. scheduled monitoring and stale refresh;
7. retryable failures with bounded backoff.

Unchanged sources may still be checked when monitoring is due, but repeated
unchanged processing is not promoted to Alpha or counted as a new need. No
customer need, monetization opportunity, or Clyde intelligence record was
fabricated during this correction. The customer-demand lane remains enabled,
but the audited window produced zero deduplicated needs and therefore zero
monetization routes.

## GoClear objective continuation

`COMPLETE_GOCLEAR_LAUNCH_READINESS` remains `ACTIVE` under governance receipt
`gov_a19f6ea2680f6a71`. Existing workstreams were not replaced:

- advanced: CRJ evidence collection and Alpha review; Research routing repair;
  portal auth/tenant source audit; offer/pricing reconciliation; existing
  Creative, Compliance, Customer Service, Social, and analytics readiness
  evidence review;
- completed in this run: bounded CRJ source acquisition and follow-up
  execution, plus the Research-to-Alpha repair;
- blocked or awaiting review: live portal end-to-end proof, a canonical READY
  GoClear social account, material pricing reconciliation, vendor activation,
  and reserved publication/launch decisions.

The portal code contains authenticated context resolution through
`tenant_memberships`, tenant/client-scoped Supabase reads, and RLS policies in
the client-portal migrations. It also contains a synthetic fallback and a
feature flag for live test-client mode. A live authenticated client proof was
not run in this correction, so portal readiness remains `PARTIAL`, not PASS.
The current route inventory covers dashboard, profile, credit, documents,
business setup/bankability, funding readiness, recommendations, resources,
messages, billing, and request review; no new customer data was created.

Pricing remains unchanged and conflicting by design pending Ray's decision:
the governed test registry contains `readiness_review_97` at $97 and draft
monthly readiness membership at $149, while the current public pricing audit
records GoClear display prices of $49/mo and $149/mo and older Stripe test
products of $100/mo and $197/mo. No material pricing mutation was made.

## Scorecard for the next audit

Track jobs executed, unique useful artifacts, new customer needs, monetization
opportunities, Alpha reviews/decisions, secondary-value routes, department
handoffs/results, Clyde intelligence, retryable-failure rate, and duplicate/no-
change rate. The next audit should require at least one fresh evidence package
to reach Alpha and should report whether that decision created a valid bounded
department result or an explicit Research-more follow-up. It should also
separate scheduled monitoring from new economic intelligence.

## Continuation and safety

The canonical `com.nexus.continuous-loop` remains active with a real heartbeat,
durable owner, and `queue_empty_does_not_stop=true`. Research, Alpha follow-up,
and GoClear objective work remain restartable without Codex. Telegram/reporting
delivery is not used as a work prerequisite. Publication, customer contact,
vendor activation, pricing changes, spend, and external PII transfer were all
`NO`.
