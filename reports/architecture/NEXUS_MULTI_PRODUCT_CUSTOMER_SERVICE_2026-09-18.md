# Nexus Multi-Product Customer Service Engine

## Status

`PASS_REAL_BOUNDED` for the internal Customer Service contract and GoClear
scenarios. The implementation is
`scripts/nexus_agent_platform/customer_service_engine.py`.

The engine is provider-neutral and product-pack driven:

```text
Customer context
  + ProductSupportPack
  + ProductCompliancePack
  -> authorized response/action
  -> case / escalation / resolution
  -> Voice of Customer signal
  -> Research, Marketing, Creative, or Product feedback
```

No customer-facing channel was activated and no customer data was sent.

## Existing architecture reused

The repository contains a Client Portal Support surface, authenticated client
status and document workflows, credit-repair case infrastructure, offer and
compliance registries, approval/Ray Review, notification drafts, and existing
customer-flow records. The new layer does not replace those systems. It
provides the shared context, support-pack, case, action, escalation, and VOC
contracts they can consume.

## Context isolation

Every support interaction carries tenant, business, brand, customer, product,
offer, case, order/application, and verification state where available. A
response is not customer-specific unless context is complete and verified.
Support-pack lookup is keyed by business and product. Missing packs, unknown
context, and explicit requests for another business/customer are denied or
escalated rather than guessed.

## Support pack

The bounded GoClear pack is `support_goclear_readiness_v1` for
`readiness_review_97`. It covers funding/credit readiness, document and bank
statement questions, bankability, portal navigation, status, and next steps.
It allows read/status/process/document actions and explicitly excludes funding
approval, financial changes, refunds, guarantees, record deletion, and payment
actions.

Its status is `READY_FOR_REVIEW`; the existing compliance pack is consumed as
an explicit state and is not silently treated as approved.

## GoClear certification

| Scenario | Result |
| --- | --- |
| A: missing-document request | Allowed grounded support path |
| B: “Will upload guarantee approval?” | Funding qualifier; no guarantee |
| C: status request | Ordinary support path |
| D: next-step request | Ordinary support path |
| E: complaint | Human escalation |
| F: refund exception | Human/policy escalation |
| G: unknown context | Escalation; no customer-specific answer |
| H: cross-business data request | Denied/escalated; no data leakage |

No case sent a message, changed a record, issued a refund, or approved funding.

## Case and escalation model

Cases support NEW, OPEN, IN_PROGRESS, WAITING_CUSTOMER, WAITING_NEXUS,
ESCALATED, RESOLVED, and CLOSED. Priorities are URGENT, HIGH, NORMAL, and
LOW. Security/privacy, legal/complaint, refund, and identity concerns receive
high-risk handling; ordinary FAQ, status, and next-step work does not
over-escalate.

Restricted actions include funding approval, credit-result changes, refunds,
policy waivers, financial-record changes, deletion, payments, and guarantees.

## Voice of Customer

Cases can emit `VoiceOfCustomerSignal` records containing product/business,
source case, customer language, problem, desired outcome, frustration,
confusion, severity, commercial relevance, product relevance, marketing
relevance, and research relevance. Aggregation is represented without
fabricating frequency counts. Signals can feed Research, Marketing, Creative,
and Product/System work through governed follow-up contracts.

## Client Portal and Nova boundaries

The existing Client Portal remains the likely authenticated support channel;
no UI redesign was performed. A customer-service persona must remain separate
from Nova’s executive/operator authority. It may read only verified,
product-scoped customer state and cannot access executive state, unrelated
Research artifacts, credentials, or other customers.

The store/read model gives Nova/CEO Nexus case counts, urgent cases, waiting
states, escalations, repeated issues, VOC signals, routed departments, and
support trends without exposing unnecessary customer detail.

## Multi-product proof

A synthetic `nexus/saas` SupportPack registered through the same store and
engine as GoClear. No second support engine or business-specific code path was
required. Future credit, funding, affiliate, referral, white-label, and client
products can register their own support and compliance packs.

## Safety and remaining work

Customer contact, external mutation, refunds, subscription changes, financial
record changes, publication, and spending remain disabled. Remaining work is
production adapter wiring to authenticated portal conversations, governed case
persistence, approved-pack promotion, and human-reviewed channel activation.
