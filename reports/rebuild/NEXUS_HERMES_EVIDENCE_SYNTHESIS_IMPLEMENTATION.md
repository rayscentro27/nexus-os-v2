# Hermes Evidence Synthesis Integration

Campaign: `HG-WP6.5-HERMES-EVIDENCE-SYNTHESIS-INTEGRATION-20260830-01`  
Baseline: `f6a555e`  
Implementation checkpoint: Phase A development only; live Telegram retest pending.

## Implemented

- Added `scripts/nexus_agent_platform/evidence_broker.py`.
- Added `scripts/nexus_agent_platform/claim_validator.py`.
- Extended the existing `AgentState` with `evidence_payload` and `claim_validation`.
- Attached scoped evidence projection and deterministic claim validation to the existing Hermes operational-read graph path.
- Preserved the existing LangGraph adapter, feature flags, deterministic router, and legacy fallback.
- Added focused regression tests for evidence classes, scoping, unsupported claims, and state round-trip.

## Runtime boundary

The Hermes/LangGraph platform remains flag-gated. This checkpoint does not activate it on the live Telegram worker and does not constitute Telegram E2E certification. The implementation is ready for fresh real Telegram tests after Ray submits varied questions.

## Evidence contract

Successful reads produce provenance-bearing FACT records. Failed or unavailable reads produce UNKNOWN records and no allowed capability. ESTIMATE and ASSUMPTION are reserved for future domain-specific projections and must carry derivation/assumption details. The validator rejects material claims that contradict unavailable evidence, approval state, or scenario semantics.

## Authority and rollback

TruthKernel remains authoritative. Hermes cannot approve gates, expand capabilities, select prohibited tools, or mutate canonical state. Existing deterministic and legacy routes remain intact; disabling the existing platform flags returns traffic to the prior route.

## Known limits

- The current graph’s operational response composer is still largely deterministic; full Hermes executive synthesis requires the later live-path integration and real Telegram verification.
- Primary-source research retrieval/verification remains the existing WP6 bounded limitation.
- No Active Operator, Research Alpha, model, service, credential, or Telegram configuration was changed.

