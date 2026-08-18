# Opportunity Engine Foundation

## Canonical model

The new opportunity engine uses one canonical opportunity record shape across existing Nexus sources.

Required fields:

- `id`
- `title`
- `category`
- `problem`
- `target_customer`
- `evidence`
- `search_demand`
- `social_signal`
- `competitive_signal`
- `commercial_intent`
- `revenue_model`
- `startup_cost`
- `ongoing_cost`
- `difficulty`
- `time_to_test`
- `risk`
- `confidence`
- `opportunity_score`
- `status`
- `recommended_next_action`

Evidence classification:

- `KNOWN`
- `INFERRED`
- `UNVERIFIED`

Statuses:

- `DISCOVERED`
- `RESEARCHING`
- `VALIDATED`
- `REJECTED`
- `PILOT_PROPOSED`
- `APPROVED`
- `BUILDING`
- `LAUNCHED`
- `MEASURING`
- `SCALING`
- `PAUSED`
- `KILLED`

## Deterministic-first scoring

Scoring is computed in Python from measurable features:

- evidence count
- demand indicators
- social signal
- commercial intent
- revenue potential
- startup cost
- ongoing cost
- difficulty
- time to test
- recency
- confidence

AI never silently overwrites deterministic scores.
If AI contributes, its rationale is stored separately from the canonical score fields.

## Reused existing sources

- Business opportunity reads
- Research intake/results
- Business model / offer summaries
- Alpha opportunity research artifacts
- Existing Hermes readiness and recommendation surfaces

## Loop integration

`opportunity_discovery_loop` now operates on a compact canonical packet:

- normalize
- dedupe
- score deterministically
- compare against prior structured state
- decide whether AI is materially necessary
- merge AI interpretation without losing canonical values

The loop remains bounded and uses zero tokens when nothing materially changes.

## Safe pilot result

A safe internal pilot was run against governed reads and research artifacts.

Observed behavior:

- duplicate opportunities were deduped
- low-signal input stayed zero-token
- material input used a compact AI synthesis path
- canonical record and business-case skeleton were preserved
- provenance remained attached to the record

## Cost observability

- `estimated_cost` is in USD
- the unit check is verified by the test suite
- the opportunity loop records deterministic-vs-AI execution share

## Verification

Focused tests passed for:

- duplicate record rejection
- zero-token low-signal path
- deterministic score stability
- AI score overwrite protection
- provenance requirements
- status transition validation
- explicit premium escalation
- compact-context enforcement
- canonical loop record writing
- cost calculation unit verification
