# Nexus Funding Claim Verification Policy V1

Status: canonical internal verification doctrine

## Rule

Research, Alpha, and Clyde use one governed pipeline. A material claim is
classified before evidence is evaluated. The source authority is determined by
the claim, not by a generic `official_source` label.

Absence from SBA.gov does not invalidate non-SBA claims. SBA.gov is authoritative
for SBA program rules, not for private lender underwriting, issuer approval
patterns, bureau pulls, credit limits, relationship banking, or other
institution-specific behavior.

Lender-specific requirements must not be generalized to all lenders. Observed
approval patterns are not guarantees and must never be presented as a private
underwriting algorithm.

## Claim routing matrix

| Claim type | Required source class | Evidence state when supported |
| --- | --- | --- |
| `SBA_PROGRAM_RULE` | SBA or applicable government/regulatory publication | `OFFICIAL_PROGRAM_RULE` |
| `LENDER_REQUIREMENT` | Named lender's official page, application, agreement, or disclosure | `PUBLISHED_REQUIREMENT` |
| `ISSUER_PRODUCT_TERM` | Named issuer's official product terms/disclosures | `OFFICIAL_PRODUCT_TERM` |
| `CREDIT_UNION_MEMBERSHIP_RULE` | Named credit union's official membership documentation | `PUBLISHED_REQUIREMENT` |
| `CREDIT_CARD_APPROVAL_PATTERN` | Observed outcomes plus multiple independent market sources | `OBSERVED_APPROVAL_PATTERN` |
| `BUREAU_PULL_PATTERN` | Observed outcomes, issuer disclosure, and multi-source evidence | `OBSERVED_APPROVAL_PATTERN` or `PARTIALLY_VERIFIED` |
| `BUSINESS_BUREAU_REPORTING` | Issuer disclosure, bureau evidence, and observed outcomes | `PARTIALLY_VERIFIED` until corroborated |
| `PERSONAL_GUARANTEE_RULE` | Named lender/issuer terms | `OFFICIAL_PRODUCT_TERM` |
| `CREDIT_LIMIT_PATTERN` | Observed outcomes plus multi-source evidence | `OBSERVED_APPROVAL_PATTERN` |
| `APPLICATION_VELOCITY_PATTERN` | Accumulated observed outcomes plus multi-source market evidence | `OBSERVED_APPROVAL_PATTERN` |
| `RELATIONSHIP_BANKING_PATTERN` | Institution publication plus observed outcomes | `PARTIALLY_VERIFIED` |
| `MARKET_PATTERN` | Multiple independent sources | `MULTI_SOURCE_MARKET_EVIDENCE` |
| `REGULATORY_RULE` | Applicable regulator or government source | `OFFICIAL_PROGRAM_RULE` |
| `PRACTITIONER_STRATEGY` | Multiple supporting sources and practitioner material | `PARTIALLY_VERIFIED` |

Evidence is also allowed to remain `ANECDOTAL_SIGNAL`, `NEXUS_INFERENCE`,
`UNVERIFIED`, `CONTRADICTED`, or `STALE`. No official source found means the
claim remains unverified; it does not mean the claim is false.

## Approval intelligence

Nexus may maintain an internal observed approval profile with institution,
product, observation count, date window, score/inquiry/utilization patterns,
relationship patterns, limits, approval/denial counts, source count, confidence,
and last refresh. It must describe the population and limitations. It must not
claim knowledge of a private underwriting algorithm or promise approval.

## Alpha and Clyde use

Alpha checks whether the evidence contains the source classes required by the
claim and records contradictions, freshness, and confidence. Clyde may produce
internal funding-readiness intelligence that separates verified facts, source
claims, unverified items, and Nexus interpretation. No client contact, lender
submission, transaction, public claim, or approval promise follows from this
policy.

The implementation lives in
`scripts/nexus_agent_platform/research/claim_verification.py` and is consumed by
the existing Intelligence Fabric and Clyde handoff consumer.
