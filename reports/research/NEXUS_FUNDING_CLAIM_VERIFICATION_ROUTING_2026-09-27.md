# Nexus Funding Claim Verification Routing — 2026-09-27

## Scope

This bounded hardening pass corrected source routing in the existing
Research → Alpha → Clyde path. No second pipeline, scheduler, or client-facing
workflow was created.

## Current architecture and defect

The existing Intelligence Fabric persisted claims with broad categories such as
`DEPARTMENT_RESEARCH` and described evidence as internal/public. The Alpha pack
preserved source rows but did not have a canonical claim-specific authority
matrix. Clyde already separated SBA evidence from lender evidence in the real
ClearValue Tax canary, but the doctrine was implicit rather than reusable.

The defect was an authority ambiguity: a generic official-source concept could
be read as universal, allowing SBA evidence to be over-weighted for non-SBA
underwriting claims or allowing a named lender fact to be generalized. This
change makes claim class, required source class, evidence state, and product
scope explicit. It does not claim that SBA overreach occurred in the certified
canary result; the existing result correctly preserved lender-specific limits.

## Real canary

Canary lineage: YouTube `gVYmkoruPDc` → Research → native Alpha receipt
`alpha_receipt_ff30fd24f38f4e34b0d9b092dae94572` → handoff
`research_handoff_237bb7a35e454ce7a186baac8832fbdd` → existing Clyde consumer.

The canary claim is a named Bank of America business-loan qualification claim.
It is classified as `LENDER_REQUIREMENT`, routes to `OFFICIAL_LENDER`, and does
not require SBA.gov. The persisted Clyde result remains `QUALIFIED_INTERNAL`.
It includes Bank of America, American Express, OnDeck, Chase, and Nav evidence,
with lender/product limitations preserved. No observed approval database was
used in this canary; the architecture supports `OBSERVED_OUTCOME_SOURCE` for a
future bounded approval-profile claim without treating it as a guarantee.

The reprocessed Clyde artifact records:

- `claim_type`: `LENDER_REQUIREMENT`
- `required_source_classes`: `OFFICIAL_LENDER`
- `sba_required`: `false`
- `sba_absence_invalidates`: `false`
- `lender_specific_must_remain_product_scoped`: `true`
- decision: `QUALIFIED_INTERNAL`
- consequential action: `false`

## Files and tests

- Added the reusable claim classifier/source matrix and evidence states.
- Wired the existing Intelligence Fabric claim contract to the classifier.
- Added verification routing to the existing Clyde internal artifact.
- Added focused Python tests for SBA non-requirement, observed approval profiles,
  and the real lender-evidence canary.
- No portal, auth, Admin, Nova, Telegram, trading, or marketing files changed.

## Assessment

`UNIVERSAL_AUTHORITY_DEFECT_FOUND=YES` as a contract/documentation gap.
`SBA_OVERREACH_FOUND=NO` in the certified gVYmkoruPDc result.
`LENDER_GENERALIZATION_DEFECT_FOUND=YES` as a preventable model risk; the new
contract keeps named product claims scoped.

No consequential action was performed.
