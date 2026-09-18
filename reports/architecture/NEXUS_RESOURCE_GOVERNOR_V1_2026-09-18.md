# Nexus Resource Governor V1

## Status

`PASS_REAL_BOUNDED` in `SHADOW` mode. The Governor evaluates, ranks, reserves,
explains, and records resource decisions but never executes a WorkerJob.
Execution remains in `temporary_worker_framework.py` and its provider adapters.

## Reused architecture

Existing routing was audited. Hermes/model routers remain responsible for model
selection, while `remote_worker.py`, the Modal provider, and the generic
WorkerJob/WorkerResult layer remain responsible for execution. No second
scheduler, worker framework, or model router was created.

## Governor contract

`resource_governor.py` provides:

- `evaluate_job`
- `eligible_providers`
- `rank_providers`
- `select_provider`
- `reserve_capacity`
- `release_reservation`
- `record_execution_result`
- `select_fallback`
- `group_batch_candidates`
- `resource_status`

Each decision includes requirement classification, provider eligibility,
explainable reasons, selected provider, fallback, shadow-mode state, and an
explicit `executed=false` marker.

## Eligibility and ranking

The Governor distinguishes capability, authorization, availability, quota,
capacity, security, and cost. Unknown quota is never interpreted as unlimited.
The ranking doctrine is the cheapest capable path: Mac is preferred for a
bounded CPU smoke job because it requires no external quota and preserves
Oracle headroom for Hermes/Nova.

Resource classes are represented as `ABUNDANT_LOCAL`, `PERSISTENT_CLOUD`,
`TEMPORARY_REMOTE`, and `TEMPORARY_GPU`. Oracle is protected by default;
Modal has existing deployment truth but unknown quota/cost; Kaggle is not
authorized.

Reservations are separate from execution and carry provider, class, job,
priority, amount, reason, timestamps, expiry, and lifecycle status.

## Scarce compute and stage routing

GPU work requires `production_ready=true`. The intended Creative gate is the
existing ProductionReadiness chain: script critique, storyboard, continuity,
prompts, claims, and output requirements must be ready before GPU eligibility.
Routine scripting, QA, captioning, overlays, and FFmpeg remain on cheaper
capable resources.

Stage-level routing is compatible with separate model reasoning, image/video
generation, FFmpeg, QA, and storage stages. The Governor does not collapse
them into one provider decision.

## Model compatibility

Existing certified routes are preserved:

- Nova chat: `openai/gpt-4o-mini`
- tool routing/research extraction: `nex-agi/nex-n2.5-pro:free`
- research synthesis/Alpha review: `google/gemini-2.5-flash`

Compatibility metadata exposes bounded escalation reasons such as tool failure,
low confidence, schema failure, quality failure, timeout, and model
unavailability. Resource Governor routing remains inactive.

## Spend and fallback policy

`AUTO_SPEND_ALLOWED=NO`. Unknown-cost or unauthorized paid execution is not
treated as free. Fallback is evaluated only among providers that still satisfy
capability, security, authorization, cost, and quota boundaries.

Kaggle authorization failure is local to Kaggle. Oracle uncertainty does not
stop Mac work. A blocked GPU job waits or remains blocked without stopping
Research, Marketing, Creative, or Hermes.

## Certification cases

| Case | Result |
| --- | --- |
| A: CPU smoke job | Mac eligible and selected; shadow-only |
| B: ready GPU video job | No eligible provider; Kaggle auth absent, other GPU capability unavailable |
| C: blocked preferred Modal path | Mac selected as bounded fallback |
| D: compatible jobs | Batch group proposed, no execution |
| E: paid/unknown-cost path | Modal marked `UNKNOWN`; Mac remains the free-capable path |
| F: GPU job without readiness | GPU gate blocks route with explicit `production_ready` reason |

## CEO/Nova view and future scheduler

`resource_status()` exposes provider availability, authorization state,
capabilities, active reservations, Governor mode, autonomous-routing state,
and execution-history count. Decision records expose what can run, why a
provider is blocked, what fallback exists, and whether work is deferred.

The result schema is ready to feed future history optimization with estimated
versus actual runtime, startup/setup/model-load/transfer/cleanup time,
resource usage, cost, quality, and failure reason. A future scheduler may
consume job ID, priority, earliest start, deadline, runtime estimate,
resource requirement, reservation requirement, quota dependency, batch group,
and defer reason. No scheduling was activated here.

## Safety

Shadow mode performed zero provider mutations. No GPU time, money, publication,
customer contact, or external action occurred. Focused Python tests cover
classification, eligibility, explainable ranking, capacity reservations,
unknown quota, scarce-compute gating, batching, model compatibility, fallback,
and shadow behavior. Python compilation passed.
