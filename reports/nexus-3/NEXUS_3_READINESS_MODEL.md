# Nexus 3.0 Readiness Model

Readiness source of truth preserved:
- buildClientFundingReadiness
- computeJourneyState
- evaluateBusinessFundingReadiness
- evaluateTierFundingReadiness
- persisted live-data adapter where enabled

Display policy:
- incomplete information remains represented as incomplete or awaiting review
- no score improvement, funding approval, deletion, or lender outcome is guaranteed
- next actions remain deterministic and capped by existing generation logic
