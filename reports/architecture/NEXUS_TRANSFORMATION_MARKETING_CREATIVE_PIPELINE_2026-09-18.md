# Nexus Transformation-First Marketing to Creative Pipeline

## Implementation status

Implemented in `src/lib/transformationCampaignContract.ts` as a typed,
storage-neutral contract over the existing campaign, brief, asset, approval,
and studio-output structures. No new table or parallel database was created.

Canonical flow:

```text
Research need and evidence
  -> Alpha QUALIFY receipt
  -> TransformationContract
  -> MarketingInput -> MarketingBrief
  -> CreativeInput -> CreativeBrief -> CreativePackage
  -> Creative QA -> internal Ray Review
  -> future measured distribution -> Research/Alpha feedback
```

## Restaurant funding-readiness proof

The bounded internal proof uses the existing qualified need
`need_f527d1db8c4d1e5de721`, Alpha reference
`alpha_qualified_need_f527d1db8c4d1e5de721`, campaign
`goclear-funding-readiness-r20b`, and offer `readiness_review_97`.

Core transformation:

> Turn funding uncertainty into a documented readiness path so the owner can
> make a clearer, better-prepared next move.

Durable contract IDs:

| Contract | ID |
| --- | --- |
| Transformation | `transformation_f35ebb47` |
| MarketingInput | `marketing_input_9f9ccd51` |
| MarketingBrief | `marketing_brief_123cdc5f` |
| CreativeInput | `creative_input_f684a482` |
| CreativeBrief | `creative_brief_95fc9ef3` |
| CreativePackage | `creative_package_1c3c9494` |
| QA receipt | `qa_75f2117a` |
| Approval | `approval_75f2117a` |
| Outcome feedback | `feedback_afb57dfe` |
| Future worker job | `worker_job_75f2117a` |

Every downstream object preserves the Research evidence references, Alpha
decision reference, transformation ID, campaign ID, and preceding contract ID.

## Governance

Claims are classified as observed fact, supported claim, hypothesis, possible
outcome, or prohibited guarantee. The contract blocks promises of funding,
approval, revenue, expansion, fabricated testimonials, or unsupported results.
The package uses possible outcomes and readiness language only; it does not
promise funding approval or revenue.

QA receipt `qa_75f2117a` is `PASS`. The revision seam is covered by a focused
test: unsafe guarantee language returns `REQUEST_REVISION`. The clean proof
needed no revision. Approval is `PENDING_RAY_REVIEW` with
`publication_authorized=false`.

## Existing storage and linkage

The canonical persistence projection targets the existing:

- `creative_campaigns`
- `creative_briefs`
- `creative_design_briefs`
- `creative_assets`
- `approvals`
- `studio_outputs`

The proof adds metadata and relations conceptually; it does not write a new
production row or alter the existing schema. Future asset output returns via
the existing `creative_assets` registry, with campaign, brief, approval, and
version lineage retained.

## Analytics and feedback

The package defines future success metrics for impressions, views, clicks, CTR,
landing visits, lead starts/completions, qualified leads, conversion,
attributable revenue, and cost where applicable. `LIVE_OUTCOMES_AVAILABLE=NO`.

Outcome feedback separates observation, interpretation, and hypothesis and
sets `causal_claim=false`. It links to the Research need and Alpha receipt so
future measured outcomes can inform both without claiming causality from
correlation.

## Future worker interface

`WorkerJobInput` and `WorkerJobOutput` are host/provider-neutral. The proof
creates a queued `MEDIA_RENDER` contract with bounded runtime, resource
requirements, artifact hashes, tool versions, logs, errors, and resource-use
fields. No Kaggle, Oracle, Mac, or external media worker is built or run.

## Visibility and next step

The contract projection gives existing operational read models the campaign,
transformation, Marketing stage, Creative stage, QA state, approval state,
asset requirements, and future worker state needed for Nova visibility. No UI
change is required.

Recommended next sequence:

1. Persist a selected qualified package through the existing campaign/brief/
   approval adapters.
2. Expose its IDs and stage states in the existing read model.
3. Attach native Creative QA scores to `creative_package_id`.
4. After human approval, run a bounded distribution and analytics test.
5. Add a worker adapter only for an explicitly approved media job.

## Safety and verification

No publication, customer contact, external mutation, site modification, paid
media, money spent, Resource Governor activation, or Kaggle worker occurred.
The focused TypeScript source and test entrypoints parse successfully with
esbuild. Repository-wide Vitest and `tsc` processes were already hanging in
this dirty worktree because of existing background processes; they were not
used as a reason to modify production systems.
