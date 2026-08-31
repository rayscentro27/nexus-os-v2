# Nova Hermes Final Claim Provenance Certification

Campaign: `HG-WP6.5-NOVA-PRIMARY-FINAL-CLAIM-PROVENANCE-AND-CURRENTNESS-CERTIFICATION-20260831-01`

## Narrow repair

The prior validator only checked currentness when the user prompt itself
requested current information. That allowed a no-tool winner follow-up to
describe model judgment as a current-market finding.

The validator now also inspects material currentness language in the draft.
It accepts the language when direct page evidence or a provenance-linked
current result is present. Otherwise it returns a bounded correction request
to Hermes. It does not ban the word `current`, force a tool call, or alter
ordinary recommendation behavior.

## Preflight

The winner and referent sequence passed through the canonical Hermes-primary
worker. The winner remained one of the supplied candidates, the first option
resolved correctly, and the final concern/winner comparison preserved both
referents.

The canonical Tesla turn executed web search and page retrieval. The retrieved
InteractiveCrypto page was dated 2026-08-23, retrieved 2026-08-31, classified
as `AUTHORITATIVE_SECONDARY`, and marked `CURRENT`. Hermes separated sourced
facts from its interpretation.

General, web, Nexus, multi-resource, Alpha, Alpha reuse, referent, and failure
regressions completed successfully. No custom runtime or A/B fanout was used.

`READY_FOR_RAY_FINAL_MINIMAL_TEST=YES`

