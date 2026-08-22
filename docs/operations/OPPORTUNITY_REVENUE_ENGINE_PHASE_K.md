# Governed Opportunity + Revenue Engine — Phase K

Phase K converts evidence-backed Alpha opportunity candidates into governed, scored, deduplicated opportunity intelligence. It does not execute revenue actions and does not claim actual revenue.

## Reconciliation

The existing Opportunity Lab and `task_requests` feeders remain supported as legacy/project-card inputs. Existing `money_opportunity_model.py`, content/affiliate feeders, the TypeScript Alpha money-opportunity seed, and historical reports remain report or legacy inputs. They are not evidence certification by themselves. The canonical Phase K state is the append-only governed `opportunities` collection, surfaced through the existing Mission Control read model. Existing `nexus_events`-style proof is represented by the governed audit stream; no second scheduler or work-order system was added.

## Contract and lifecycle

Canonical records use `nexus.opportunity.v1` and deterministic scoring uses `nexus.opportunity-scoring.v1`. Records retain title, business/category, monetization path, target audience, Alpha research job and pack references, evidence references, freshness, score components, value assumptions, dependencies, risks, unknowns, contradictions, and advisory next action.

Lifecycle states are `CANDIDATE`, `QUALIFIED`, `NEEDS_RESEARCH`, `NEEDS_RAY_REVIEW`, `APPROVED_FOR_PLANNING`, `PARKED`, `REJECTED`, `CONVERTED_TO_WORK_ORDER`, `STALE`, and `CLOSED`. There is no `EXECUTED` opportunity state; execution state belongs to governed work orders.

An Alpha candidate can become `QUALIFIED` only when its evidence references resolve through the supplied Alpha research pack and the evidence is fresh enough for the job requirement. Missing, stale, malformed, or legacy-only evidence remains `NEEDS_RESEARCH` or `STALE`. Legacy records are explicitly marked `UNVALIDATED_LEGACY`, and their value estimate is `UNKNOWN`.

## Scoring and value

Scoring is deterministic and inspectable. It weights evidence strength, revenue potential, speed to value, launch cost, effort, risk, client value, business fit, recurring revenue, strategic fit, confidence, and freshness. Risk, cost, and effort are explicit penalties. LLM output cannot overwrite canonical scores.

Pipeline value is not actual revenue. Value estimates are classified as `KNOWN`, `EVIDENCE_BACKED_ESTIMATE`, `ASSUMPTION`, or `UNKNOWN`, expose low/expected/high values and assumptions, and keep actual leads, sales, revenue, cost, and margin unknown until attributable outcomes exist.

## Deduplication and governance

Identity uses normalized title, category, business, monetization path, and target audience. Re-ingesting the same Alpha candidate produces `DUPLICATE_SUPPRESSED` and an audit event rather than a second record. Related variants can remain distinct when their canonical identity differs.

The engine may validate, score, rank, mark stale, request research, and request Ray review. A review request uses the existing governed approvals layer. Only an explicit approved decision can prepare a linked existing work order; the Phase K handoff is structural and performs no external action. Publishing, outreach, affiliate applications, spending, charging, live pricing changes, grants, funding submissions, trading, and client communication remain unavailable.

## Mission Control and Hermes

Mission Control exposes an optional Opportunity Engine section with health, active/qualified/needs-research/needs-Ray/approved/stale counts, top opportunity, pipeline estimate classification, and freshness. Opportunity failures do not degrade core health. Hermes must consume this canonical read model for opportunity questions rather than inventing independent scores.

## Live certification

The live GoClear certification imported three bounded public-context opportunity types from a real Alpha research pack: a direct offer, a partner/affiliate research candidate, and a content/SEO candidate. The same Alpha candidate was re-ingested and suppressed as a duplicate. An existing legacy candidate remained `NEEDS_RESEARCH`/`UNVALIDATED_LEGACY`. One qualified opportunity generated a pending Ray review request; no approval was fabricated and no external action occurred.

Phase K prepares the governed pipeline for the Phase L GoClear Revenue Operations Dashboard. It does not build the full Revenue Hub.
