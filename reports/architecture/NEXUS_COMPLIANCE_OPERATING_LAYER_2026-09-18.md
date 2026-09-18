# Nexus Compliance Operating Layer

## Status

`PASS_REAL_BOUNDED`. The canonical implementation is
`scripts/nexus_agent_platform/compliance_engine.py`. It is a decision and
evidence layer, not a publisher, scheduler, legal-certification system, or
customer-service runtime.

Existing safeguards were reused conceptually: content marketing policy
(drafts-only and blocked guarantees), approval/Ray Review, outcome analytics
non-causality language, transformation claim controls, and Creative QA. No
duplicate compliance system or production publishing path was created.

## Claim model

Supported classes include observed fact, supported factual claim, supported
marketing claim, opinion, hypothesis, possible outcome, comparison, test
result, testimonial, forward-looking statement, unverified claim, and
prohibited guarantee. Each review carries claim ID, evidence references,
scope, limitations, qualifiers, risk, and review status.

Intensity levels preserve useful marketing:

- Level 1: plain factual statement
- Level 2: strong directly supportable statement
- Level 3: compelling curiosity/transformation framing with support
- Level 4: high-risk wording requiring strong evidence or prominent qualification
- Level 5: unsupported, misleading, or prohibited

Levels 2–3 remain allowed. The system evaluates reasonable viewer
interpretation, material omissions, qualifier placement, and headline/body/CTA
consistency. A rejected claim produces the strongest supported alternative,
not merely “rejected.”

## Domain policies

Funding and credit content must distinguish verified public/lender evidence,
customer-reported experience, common market language, and hypothesis. Approval,
rate, amount, timeline, score movement, deletion, and lender-requirement claims
require scoped evidence and cannot become guarantees.

Trading content must preserve test period, market, fees, slippage, methodology,
out-of-sample status, repainting, and limitations. It attacks the claim, not
the person. “We could not reproduce the result” is permitted when supported;
“this creator is a scammer” is blocked.

Truth/testing content follows:

1. What was claimed
2. What was tested
3. What happened
4. Why results differed
5. Limitations
6. What viewers can learn
7. Better approach

## Secondary value routing

Alpha rejection no longer implies discard. `secondary_value_review` preserves
the original Alpha decision, reason, evidence, commercial relevance, and
routes the item to content, education, comparison, affiliate alternative,
lead generation, customer-pain signal, product gap, marketing intelligence,
research insight, or archive.

The bounded trading example routes a failed reproduction to comparison/content
with reproducibility disclosures. The operationally unsuitable AI video tool
case can route to education/comparison: free/manual access may be useful to
users while not being automatable for Nexus.

## Compliance packs and integration

`ProductCompliancePack` supports business/product/version/status, allowed and
prohibited claims, evidence, disclosures, qualifiers, human escalation,
privacy/consent/refund/complaint/retention placeholders, and Marketing/Creative
rules. Statuses are DRAFT, EVIDENCE_PENDING, READY_FOR_REVIEW, APPROVED, and
RETIRED. Global approved-pack enforcement is not activated in this bounded
compatibility step.

Marketing briefs should carry pack, claim, evidence, disclosure, prohibited
claim, and review references. Creative packages should carry claim constraints,
prohibited phrases, disclosure placement, testimonial restrictions, and
comparison/trading/funding restrictions.

The future Customer Service contract is support response plus support pack plus
compliance pack, yielding an allowed response/action or escalation. It is
defined but not activated.

Every meaningful review can emit a compliance receipt with subject, claims,
decision, evidence, issues, required changes, disclosures, escalation, and
timestamp. Nova can use those receipts to explain blocked claims, missing
evidence, allowed wording, disclosures, human review, and secondary routes.

## Safety boundary

No publication, advertising, customer contact, spending, trading execution,
funding decision, social account, or legal certification occurred. Human review
is reserved for material financial claims, ambiguous testimonials, legal or
privacy/security uncertainty, complaints, and other high-risk boundaries.
