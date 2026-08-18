# Hermes Governed Learning Benchmark — Phase 12

Status: `PROPOSAL_ONLY_NO_AUTONOMOUS_MUTATION`

The engine reads the existing runtime loop ledger, builder ledger, Phase 9 structured pilot record, and Phase 11 Daily Brief. Source priority is explicit: runtime ledgers, canonical structured state, governed data, generated structured reports, then narrative summaries.

## Detector result

- repeated unchanged AI use: `NO_PROPOSAL`
- excessive model tier: `NO_PROPOSAL`
- low-value loop: `NO_PROPOSAL`
- retry-heavy worker: `NO_PROPOSAL`
- duplicate research source: `STRUCTURED_PROPOSAL_CANDIDATE`
- stale opportunity: `NO_PROPOSAL`
- high tokens per success: `NO_PROPOSAL`
- deterministic candidate: `STRUCTURED_PROPOSAL_CANDIDATE`
- worker routing candidate: `NO_PROPOSAL`

Two observations and two proposals were produced. They are both `PROPOSED`, require approval, have no approval ID, and contain sandbox test, success, failure, and rollback criteria.

## Current candidates

1. `DEDUPE_POLICY_CHANGE` for the Crawl4AI research source. The measured duplicate rate is `0.5` from `8` collected source records and `4` removed duplicates.
2. `MAX_AI_CALLS_CHANGE` for the verified deterministic loop class. Current evidence shows repeated verifier-passing, zero-AI executions.

## Governance boundary

The engine does not modify loop cadence, model tiers, token budgets, dedupe policy, worker routing, opportunity weights, code, deployments, approvals, or production systems. Candidate comparison metrics remain empty until a separately authorized sandbox test runs. No AI calls are required for the current arithmetic and threshold decisions.
