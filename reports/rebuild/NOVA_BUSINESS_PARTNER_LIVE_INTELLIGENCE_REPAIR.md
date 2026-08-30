# Nova Business-Partner Live Intelligence Repair

Campaign: `HG-WP6.5-NOVA-BUSINESS-PARTNER-LIVE-INTELLIGENCE-REPAIR-20260830-01`

Baseline: `afee83f`

## Scope

This checkpoint repairs the shared Nova pre-model decision boundary. It does
not add a framework, change Nova's authority, execute live Telegram requests,
or certify a real Telegram result.

## Root causes addressed

- Advisory and analytical wording could fall through to the broad planner and
  be reduced to a nearby factual lookup, such as a client count.
- Company context was injected using a narrow keyword list, so some business
  questions did not receive the bounded current context needed for reasoning.
- Recent research used the legacy Hermes history adapter before the structured
  Alpha decision artifact, making current research retrieval less reliable.

## Repair

Nova now records a bounded question type before capability selection:
`FACTUAL`, `ANALYTICAL`, `ADVISORY`, `RESEARCH`, `OPERATIONAL`, or
`GENERAL_CONVERSATION`. Advisory/analytical requests use reasoning first unless
they explicitly ask for a current operational brief. Research reads prefer the
canonical Alpha decision artifact and retain an explicit legacy fallback.

The existing governed Nexus submission path remains unchanged: Nova may submit
a request, but Nexus and TruthKernel retain authority, eligibility, execution,
verification, and receipts.

## Verification

Focused Nova, governance, daily-brief, and canonical reasoning regressions:
140 passed. This is development evidence only. Fresh real Telegram retesting is
required before any E2E certification.
