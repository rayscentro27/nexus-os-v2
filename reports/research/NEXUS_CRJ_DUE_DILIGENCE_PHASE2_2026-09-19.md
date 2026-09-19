# Nexus CRJ due-diligence phase 2

Date: 2026-09-19
Objective: `crj-goclear-capability-research-v1`

## Evidence completed through the existing Research → Alpha path

The first Alpha receipt (`alpha_receipt_a3db4882e2dd4ee9b413a2c0acc3b89f`) requested more evidence on pricing/trial terms, customer-service detail, and software/integration fit. Three bounded follow-up work items were dispatched through the existing queue and worker:

| Evidence lane | Source | Result | Alpha state |
|---|---|---|---|
| pricing / credits / trial | https://creditrepairjunkies.com/disputeforme-3471-8407 | package `package_a548f93827aa92f6c771` returned | `RESEARCH_MORE` |
| customer-service outsourcing | https://creditrepairjunkies.com/customer-service-outsourcing | duplicate unchanged; no new package | existing evidence remains `RESEARCH_MORE` |
| dispute outsourcing / white-label | https://creditrepairjunkies.com/dispute-outsourcing | duplicate unchanged; no new package | existing evidence remains `RESEARCH_MORE` |

The public pages provide bounded directional evidence about dispute outsourcing, white-label positioning, trial language, and customer-service outsourcing. They do not establish a complete vendor diligence record for integration/API/webhook behavior, contractual terms, customer-support performance, or unit economics. No vendor was contacted or activated.

## Alpha review 2

The three follow-up review attempts remain `RESEARCH_MORE`:

- pricing: detailed pricing, credit consumption, and trial terms still require source-specific confirmation;
- customer service: scalable pricing and independently verifiable testimonials/performance remain open;
- dispute outsourcing: specific software compatibility and integration details remain open.

The correct decision is not to force `QUALIFY`. CRJ remains a monitored, research-more candidate.

## Operating-model comparison

| Model | Responsibility | Automation fit | Dependency / risk | Current evidence state |
|---|---|---|---|---|
| A — disputes only | CRJ performs bounded dispute work; GoClear owns customer relationship and readiness workflow | Potentially high if intake/status exchange is documented | vendor dependency and customer-data exchange | pricing and integration evidence incomplete |
| B — disputes + outsourced support | CRJ or partner handles disputes plus bounded customer service | Medium; requires case/status and support handoff interfaces | higher privacy, QA, and customer-experience dependency | support pricing/performance evidence incomplete |
| C — near-full-service / white-label | vendor carries most fulfillment under GoClear-facing brand | Medium to low until systems and controls are proven | highest vendor, privacy, compliance, and margin dependency | white-label positioning observed; operating proof incomplete |
| D — GoClear operation + bounded outsourced disputes | GoClear owns customer, support, compliance, and workflow; CRJ handles a bounded fulfillment unit | Highest control and clearest staged integration | internal labor remains; vendor scope must stay narrow | operationally plausible, but integration and economics remain unverified |

No model is selected for Ray. This is a decision package, not an activation decision.

## Billing and legal boundary

`GoClear → vendor` payment for fulfillment is distinct from `customer → GoClear` payment for any credit-related service. Public vendor pricing language cannot be reused as a consumer billing model. Open review items are: federal and applicable state/jurisdiction questions, advance-fee/payment-timing treatment, telemarketing implications where applicable, customer disclosures, written vendor/customer agreements, refund/cancellation terms, privacy/security representations, and final compliance/legal review. No legal conclusion is asserted here.

## Next governed action

Keep the objective in `MONITORING` / `RESEARCH_MORE` and let the existing Research/Alpha runtime pursue only source-backed gaps. Do not contact, contract with, pay, or activate CRJ until the missing evidence and reserved human/legal decisions are resolved.
