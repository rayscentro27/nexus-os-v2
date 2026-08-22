# Nexus SEO + Growth Operations — Phase M

## Status

Phase M connects the existing SEO Keyword Scout, SEO marketing feeder, Alpha
evidence research, Phase K Opportunity Engine, and Phase L Revenue Truth Hub.
It is draft-only and review-gated. It does not publish, send, spend, schedule,
or mutate public/customer systems.

## Reconciliation

- `scripts/research/seo_keyword_scout.py` remains the bounded manual CSV scout.
- `scripts/automation/feeders/seo_marketing_project_feeder.py` remains the
  compatibility adapter for Growth Department task cards.
- Alpha and Crawl4AI remain the evidence path for public competitor research.
- Phase K remains canonical for business opportunity qualification, scoring,
  deduplication, and Ray review.
- Phase L remains canonical for observed leads, conversions, revenue, and
  measurement truth.
- Historical SEO reports and candidates remain legacy inputs, not live metrics.

## Canonical growth experiment

`nexus.growth-experiment.v1` is persisted in the governed local store. It
retains the originating opportunity/research/pack/evidence references, topic,
intent, target offer, hypothesis, baseline, intended metric, risks,
dependencies, freshness, approval state, and explicit `external_action_performed=false`.

Growth status is separate from publication. `NEEDS_RAY_REVIEW`,
`DRAFTING`, `MEASUREMENT_PENDING`, and `RESULT_OBSERVED` are analytical or
governed states; no automatic `PUBLISHED` state exists.

## Truth and measurement

Manual keyword imports are classified `MANUAL_REVIEWED`; search volume,
ranking, traffic, and CPC are not represented as live observations unless a
connected source proves them. With Search Console and Analytics disconnected,
baseline and outcome values remain `UNKNOWN` / `MEASUREMENT_PENDING`, never
zero. A growth recommendation is not revenue, and a Phase K opportunity
estimate is not an observed conversion.

## Evidence and briefs

Competitor findings retain canonical Alpha/Crawl4AI evidence references. Content
gaps are deterministic (`NEW_PAGE`, `REFRESH_EXISTING`, `SUPPORTING_CONTENT`,
or `NEEDS_RESEARCH`). Briefs are internal drafts and mark unsupported claims
`NEEDS_SOURCE`; they prohibit guaranteed funding, approval, score, ranking, or
income claims.

Public technical audits are bounded HTTPS reads and exclude admin, client,
dashboard, and login paths. Lighthouse is reported as `NOT_AVAILABLE` unless a
real supported result exists.

## Mission Control and Hermes

Growth Operations is an optional read model with experiment counts, Ray-review
state, measurement status, source connections, freshness, and core-health
isolation. Hermes-facing answers read canonical growth state and disclose when
traffic/conversion measurement is unavailable.

## Certification boundaries

The Phase M certification scenarios use public GoClear/competitor context only:
keyword/topic classification, bounded competitor evidence, content-gap and
brief generation, public technical checks, Phase K handoff, legacy adaptation,
duplicate suppression, stale handling, and measurement-pending truth. Public
publication, email/SMS, social posting, advertising, affiliate enrollment,
Stripe mutations, and client-PII access remain unavailable.

Next phase: governed Business Active Operator growth work after Ray approval.

## Live certification evidence

The bounded competitor run used the public Nav business-credit page through the
existing Alpha → Nexus evidence bridge → Modal/Crawl4AI path. It produced a
complete Alpha pack/report/receipt with canonical evidence reference
`ev-8874c37fddb5461287d2` and remained public-evidence-only.

The resulting GoClear growth experiment is linked to the existing Phase K
`NEEDS_RAY_REVIEW` opportunity and targets the Phase L
`readiness_review_leads` metric. Its current measurement state is
`MEASUREMENT_PENDING` / `UNKNOWN` because Search Console and Analytics are not
connected. A replay of the same candidate was `DUPLICATE_SUPPRESSED`; the
historical manual keyword candidate remains `NEEDS_RESEARCH`.

The public GoClear readiness page returned an observed HTTP 200 technical audit
with Lighthouse `NOT_AVAILABLE`; no page mutation occurred. Mission Control
reports Growth Operations `HEALTHY`, optional, and independent of core health.
