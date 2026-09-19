# Nexus Governance Operating System

Status: `PASS_REAL_BOUNDED`
Implementation commit: `a98e6c87d9ff6a802203de6a30643523f52c1af9`

## Purpose

`scripts/nexus_agent_platform/governance_engine.py` is the canonical authority
and policy decision layer. It does not execute work, publish, contact
customers, spend, or replace the existing approval, compliance, worker,
Resource Governor, or continuous-runtime systems. It evaluates an action,
returns an explainable decision, and emits a governed audit receipt through the
existing append-only `data/governed/audit.jsonl` store.

## Existing controls reused

- `governed/approvals.py`, `policy_gate.py`, `work_orders.py`, and `engine.py`:
  approval-bound execution and existing work-order lifecycle.
- `human_gate_router.py`: exact, scoped human-gate responses.
- `compliance_engine.py`: claim, disclosure, and compliance decisions.
- `social_distribution.py`: tenant/business/brand isolation and pre-publish
  controls.
- `customer_service_engine.py`: support context and restricted actions.
- `resource_governor.py`: provider eligibility/ranking remains in shadow mode.
- `company_objective_router.py` and the continuous Research runtime: objective
  decomposition and continuation remain their existing responsibilities.

The audit found no need for a second scheduler, approval database, provider
router, or governance runtime. Existing controls are real or bounded-real;
the new layer is the missing common authority vocabulary and decision receipt.

## Authority model

Subjects are explicit: Ray, CEO Nexus, Nova, Research, Alpha, Marketing,
Compliance, Creative, Customer Service, Social Distribution, Funding/Clyde,
Credit, Systems, Trading, Resource Governor, temporary workers, human
specialists, and external vendors.

Action classes cover internal reads/artifacts/work routing, local/free compute,
customer data, external contact, publication, spend, contracts, refunds,
funding/credit decisions, trading, secrets, and security changes.

Decision tiers:

1. `TIER_0_AUTONOMOUS`: routine low-risk reads and governed analysis.
2. `TIER_1_AUTONOMOUS_WITH_RECEIPT`: bounded internal artifacts, routing,
   local/free compute, and work creation.
3. `TIER_2_POLICY_GATED`: policy conditions must pass before use.
4. `TIER_3_HUMAN_APPROVAL`: external, financial, publication, customer-impact,
   contract, security, or reserved decisions.
5. `TIER_4_PROHIBITED`: actions violating isolation or sensitive-data policy.

Ray retains final authority over material spend, recurring paid commitments,
publication launch, contracts, security overrides, credential ownership,
financial transfers, regulated/high-risk exceptions, cross-business overrides,
and live trading capital. Nova and CEO Nexus may prioritize and coordinate
within that boundary; neither may silently override Compliance, spend, publish,
expose restricted data, or alter security policy.

## Checks and balances

Research discovers and verifies; Alpha challenges and qualifies; Marketing
frames offers and transformations; Compliance constrains claims without owning
strategy; Creative produces governed assets; QA/approval can reject; Customer
Service resolves only supported cases; Social prepares only pre-publish
packages; Resource Governor selects resources only within policy; workers only
execute assigned jobs. A department cannot silently grant another department's
authority.

## Failure, retry, and self-repair

`LOCAL_BLOCKER != GLOBAL_STOP`, `EMPTY_PROJECT_QUEUE != GLOBAL_STOP`,
`JOB_TIMEOUT != NEXUS_TIMEOUT`, and `WORKER_FAILURE != COMPANY_STOP`.

Retry categories are `RETRYABLE_INTERNAL`, `RETRYABLE_EXTERNAL`, `REROUTABLE`,
`WAIT_FOR_DEPENDENCY`, `HUMAN_REQUIRED`, `PERMANENT_FAILURE`, and
`POLICY_BLOCKED`. Retries are bounded. Ordinary internal repair is allowed
when it is reversible, non-destructive, non-spending, and preserves security.

## CRJ real governance case

Objective: `crj-goclear-capability-research-v1`
Observed state: `FAILED_RETRYABLE`
Observed failure: existing processor received an empty source URL and raised
`unknown url type: ''`.

Governance receipt: `gov_c27440437814363d`

Decision: `ALLOW`, `TIER_1_AUTONOMOUS_WITH_RECEIPT`; Ray is not required.
The permitted repair is to inspect the objective, remove the empty-source
dispatch, and reroute through the existing multi-source Research acquisition.
No CRJ URL or conclusion was invented. The objective remains
`FAILED_RETRYABLE_PENDING_GOVERNED_REPAIR` until the existing Research/System
path executes the repair and writes its own result receipt. This is a local
repairable blocker, not a company stop.

## Spend, data, and provider boundaries

`AUTO_SPEND_ALLOWED=NO`. Unknown price is not treated as free. Free Mac,
protected Oracle, and known free Kaggle quota remain subject to data,
capability, quota, and workload policy. The Resource Governor remains
`SHADOW`; it cannot grant itself spend or data-export authority.

Data classes are `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `CUSTOMER_PII`,
`FINANCIAL_SENSITIVE`, `CREDENTIAL_SECRET`, `REGULATED`, and
`BUSINESS_RESTRICTED`. Temporary workers receive no customer PII, bank
statements, credit reports, credentials, or restricted secrets. Tenant,
business, brand, customer, campaign, and credential boundaries remain hard
blocks.

Publication is `APPROVAL_REQUIRED` for the GoClear campaign. Customer contact,
refund exceptions, legal/privacy/security issues, and high-risk financial
representations require the existing support/compliance/human paths.

## Approval scope and emergency controls

Approvals are bound to actor, action, business, project/campaign, provider,
amount where applicable, scope, and expiration. A bounded approval never
becomes a permanent blanket authorization. Overrides require the specific
policy, reason, Ray authorization, scope, expiration, and a receipt.

Pause scopes are job, department, provider, business, external publishing,
customer contact, or company. A scoped pause leaves unrelated authorized work
running when safe.

## Certification cases

| Case | Result |
|---|---|
| A. Normal public Research | Allow autonomously with receipt |
| B. Retryable parser failure | Repair/retry/reroute; no Ray by default |
| C. Free Kaggle CPU work | Policy/Governor evaluation; no spend |
| D. Unverified GPU work | Block until production/capability evidence exists |
| E. GoClear public social post | Ray approval required |
| F. Authenticated ordinary status support | Allowed through Support + Compliance packs |
| G. Refund exception | Human escalation |
| H. GoClear to Apex account | Blocked by business/brand isolation |
| I. Credit report to Kaggle | Prohibited sensitive-data export |
| J. Paid Modal | Human spend approval required |
| K. CRJ missing source | Governed internal repair/reroute |
| L. Provider/department failure | Unrelated work continues |

## Tests and safety

Focused governance, Resource Governor, Compliance, and Social Distribution
tests: `28 passed`. Python compilation and `git diff --check` passed. No
publication, customer contact, spend, contract commitment, financial
transaction, trade, or credential mutation occurred.

## Remaining blockers

- CRJ still needs the existing Research/System repair to execute and produce a
  valid source-backed result; this report does not invent one.
- Resource Governor remains shadow-only.
- GPU capability remains unproven; no governance change activates it.
- Jurisdiction-specific legal policy remains a human/compliance responsibility.

## Next machine action

Wire the existing Research retry/reroute consumer to the governance receipt for
the CRJ objective, then continue normal Research/Alpha operation. Keep all
external publication, customer contact, paid compute, and live financial
actions approval-gated.
