# Nexus Credit & Funding Research Routing Plan

**Generated**: 2026-07-03  
**Purpose**: Define how research artifacts route to workflows, outputs, and approval gates

---

## Routing Rules

### Credit Repair Research → Credit/Funding Readiness Knowledge

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| Credit report analysis | Credit readiness knowledge base | Admin notes, scorecard inputs | Admin-only |
| Dispute letter strategies | Dispute workflow config | Draft letters (approval-gated) | Ray Review |
| Score improvement research | Credit score improvement knowledge | Client education (approved) | Ray Review |
| Negative item removal | Dispute strategy research | Admin notes, draft letters | Ray Review |
| Credit monitoring options | Client education | Partner offer research | Ray Review |
| Credit builder loans | Funding readiness research | Admin notes, client education | Ray Review |

### Utilization Research → Scorecard Recommendation Logic

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| Utilization scoring | Readiness scorecard | Score inputs | Auto (deterministic) |
| Utilization reduction strategies | Credit improvement knowledge | Client education (approved) | Ray Review |
| Statement date research | Scorecard timing | Admin notes | Admin-only |
| Balance transfer options | Funding readiness | Client education (approved) | Ray Review |

### Business Setup Research → Business Setup Checklist

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| LLC formation | Business setup checklist | Checklist items | Admin-only |
| EIN registration | Business setup checklist | Checklist items | Admin-only |
| DUNS registration | Business setup checklist | Checklist items | Admin-only |
| NAICS code selection | Business setup checklist | Checklist items | Admin-only |
| Registered agent | Business setup checklist | Checklist items | Admin-only |
| Business address | Business setup checklist | Checklist items | Admin-only |
| Business phone | Business setup checklist | Checklist items | Admin-only |
| Business bank account | Business setup checklist | Checklist items, affiliate research | Ray Review |

### Business Funding Research → Funding Readiness Plan

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| Business credit cards | Funding readiness research | Admin notes, client education | Ray Review |
| Business lines of credit | Funding readiness research | Admin notes, client education | Ray Review |
| SBA loans | Funding readiness research | Admin notes, client education | Ray Review |
| Community bank lending | Funding readiness research | Admin notes, client education | Ray Review |
| Online lenders | Funding readiness research | Admin notes, client education | Ray Review |
| Revenue-based financing | Funding readiness research | Admin notes, client education | Ray Review |

### Grant Research → Grant Opportunity Review

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| Federal grants | Grant opportunity research | Admin notes, client education | Ray Review |
| State/local grants | Grant opportunity research | Admin notes, client education | Ray Review |
| Minority business grants | Grant opportunity research | Admin notes, client education | Ray Review |
| Startup grants | Grant opportunity research | Admin notes, client education | Ray Review |
| Industry-specific grants | Grant opportunity research | Admin notes, client education | Ray Review |

### Lender Research → Admin-Only Funding Match Notes

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| Bank lending criteria | Lender matching notes | Admin-only | Ray Review |
| Credit union requirements | Lender matching notes | Admin-only | Ray Review |
| SBA lender requirements | Lender matching notes | Admin-only | Ray Review |
| Online lender criteria | Lender matching notes | Admin-only | Ray Review |
| Underwriting research | Lender matching notes | Admin-only | Ray Review |

### Affiliate Research → Ray Review / Affiliate Offer Approval

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| Bank affiliate programs | Affiliate offer research | Admin notes, Ray Review proposal | Ray Review |
| Credit monitoring affiliates | Affiliate offer research | Admin notes, Ray Review proposal | Ray Review |
| LLC formation affiliates | Affiliate offer research | Admin notes, Ray Review proposal | Ray Review |
| Mailing affiliates | Affiliate offer research | Admin notes, Ray Review proposal | Ray Review |
| Bookkeeping affiliates | Affiliate offer research | Admin notes, Ray Review proposal | Ray Review |

### Compliance Research → Policy Guardrail Updates

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| FCRA compliance | Compliance guardrails | Policy updates, guardrail changes | Ray Review |
| FDCPA compliance | Compliance guardrails | Policy updates, guardrail changes | Ray Review |
| Credit repair licensing | Compliance guardrails | Policy updates, guardrail changes | Ray Review |
| FTC disclosure requirements | Compliance guardrails | Policy updates, guardrail changes | Ray Review |
| State regulations | Compliance guardrails | Policy updates, guardrail changes | Ray Review |

### Client Education → Client Portal Education Drafts

| Input Category | Route To | Output Type | Approval |
|----------------|----------|-------------|----------|
| Credit report education | Client education drafts | Client-facing content | Ray Review |
| Utilization education | Client education drafts | Client-facing content | Ray Review |
| Business credit education | Client education drafts | Client-facing content | Ray Review |
| Fundability education | Client education drafts | Client-facing content | Ray Review |
| Grant education | Client education drafts | Client-facing content | Ray Review |

---

## Routing Table (Summary)

| Research Category | Primary Route | Secondary Route | Approval Gate |
|-------------------|---------------|-----------------|---------------|
| credit_repair | Credit readiness knowledge | Dispute workflow | Ray Review |
| credit_utilization | Scorecard logic | Credit improvement knowledge | Ray Review |
| business_setup | Business setup checklist | Affiliate research | Admin-only |
| fundability | Funding readiness plan | Client education | Ray Review |
| business_funding | Funding readiness plan | Client education | Ray Review |
| grants | Grant opportunity review | Client education | Ray Review |
| lender_program | Lender matching notes | Admin-only | Ray Review |
| affiliate_offer | Affiliate offer approval | Ray Review | Ray Review |
| compliance | Policy guardrails | Compliance notes | Ray Review |
| client_education | Client education drafts | Client portal | Ray Review |
| manual_note | Depends on content | Depends on content | Depends |

---

## Anti-Routing Rules (What Cannot Be Routed)

| Item | Reason |
|------|--------|
| Direct bureau contact | Blocked by design |
| Direct lender applications | Blocked by design |
| Automated dispute sending | Blocked by design |
| Payment collection | Blocked by design |
| Email/SMS sending | Blocked by design |
| Social publishing | Blocked by design |
| Client data exposure | Blocked until secure workflow |
| Funding approval guarantees | Blocked by compliance |
| Credit score guarantees | Blocked by compliance |
| Legal advice | Blocked by licensing |
