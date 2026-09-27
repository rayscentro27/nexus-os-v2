# GoClear Credit-Repair Outsourcing / Fulfillment Strategy

Research request: `research_request_credit_repair_fulfillment_20260927`  
Owner: `RESEARCH` → return target: `CLYDE_CREDIT`  
Research date: 2026-09-27  
Scope: public-source, non-PII strategy research only. No provider was contacted,
no account was created, and no client information was transmitted.

## Executive conclusion

GoClear should not build a full credit-repair dispute operation first. The
lowest-risk sequence is:

1. **Referral-first pilot** with a specialist that bills and contracts directly
   with the consumer, supplies milestone visibility, and accepts only
   consented referrals.
2. **Hybrid evaluation** only after state coverage, contracts, data controls,
   complaint history, and service-level evidence pass review: GoClear owns the
   relationship, education, funding-readiness context, and re-entry to the
   funding pipeline; the specialist owns regulated dispute fulfillment.
3. **White-label** only if a provider can prove the required state/federal
   compliance, client-contract ownership, security, audit trail, cancellation,
   refund, and data-return terms. A branded portal alone is not sufficient.

This is a recommendation to test an operating structure, not permission to
refer customers, sign a vendor, collect fees, or make a credit-repair claim.
Legal counsel should review the final structure for every state in which
GoClear will market, contract, or perform services.

## Regulatory baseline

- The CFPB says credit-repair organizations cannot request or receive payment
  before completing promised services; telemarketed services have additional
  timing and result-report requirements. Consumers have a three-business-day
  cancellation right. Source: [CFPB credit-repair guidance](https://www.consumerfinance.gov/ask-cfpb/how-can-i-tell-a-credit-repair-scam-from-a-reputable-credit-counselor-en-1343/).
- The FTC says credit-repair companies may not misrepresent results, remove
  accurate and timely negative information, or charge prohibited advance fees.
  Source: [FTC consumer guidance](https://consumer.ftc.gov/consumer-alerts/2026/01/spot-scams-when-fixing-your-credit).
- California requires a Credit Services Organization operating there to file
  and receive a registration certificate; registration is not an endorsement
  of compliance. The California AG also describes a $100,000 bond/deposit
  requirement in its application material. Source: [California DOJ CSO
  registration](https://oag.ca.gov/node/22352).
- Texas requires CSO registration before conducting business and has separate
  security/bond rules; Texas states that advance consideration is permitted
  only under the specified bond/surety-account conditions. Sources: [Texas
  Secretary of State CSO FAQ](https://www.sos.state.tx.us/statdoc/faqs2800.shtml)
  and [Texas Finance Code Chapter 393](https://statutes.capitol.texas.gov/DocViewer.aspx?DocKey=FI%2FFI.393&ExactPhrase=False&HighlightType=1&Phrases=98%283%29&QueryText=).
- The CFPB's Lexington Law/CreditRepair.com enforcement history is a material
  vendor-screening warning: the court concluded that the companies engaged in
  illegal upfront fees and deceptive bait-and-switch marketing. Source:
  [CFPB case page](https://www.consumerfinance.gov/enforcement/payments-harmed-consumers/payments-by-case/lexlaw/).

These sources establish compliance gates, not a complete 50-state legal
opinion. GoClear must identify its actual target states, role, compensation,
marketing channel, and whether it will touch consumer reports before launch.

## Operating-model comparison

| Model | GoClear responsibility | Provider responsibility | Client responsibility | Economics / pricing evidence | Main advantages | Main risks |
|---|---|---|---|---|---|---|
| Build internally | Intake, contract, disclosures, disputes, bureau/furnisher communications, status, complaints, billing, state compliance | None | Documents, truthful issue identification, authorizations, participation | Unknown; requires people, compliance, secure case system, legal review | Maximum control and learning | Highest regulatory, staffing, security, and execution burden; not recommended as first step |
| Outsourced specialist | Relationship and funding context; only minimum necessary referral data | Contract, intake, dispute work, client billing, status, complaints, cancellations | Consent, documents, accurate dispute basis, decisions | Usually quote-based or consumer plan; must obtain full schedule | Faster capability and specialist process | Vendor quality, state coverage, data-sharing, client ownership, and continuity risk |
| White-label fulfillment | Brand, marketing, client relationship, disclosures, vendor oversight, escalation | Behind-brand dispute work, case system, portal/status, operations | Same as above; must understand provider relationship | Credloom publicly lists $59/$89/$149 monthly service tiers billed in arrears; other white-label terms are quote-based | Seamless GoClear experience and reusable portal | GoClear may assume regulatory/advertising/complaint liability; brand opacity can make diligence harder |
| Referral partnership | Education and referral only; no promise or dispute advice; consented handoff | Contract, client, billing, dispute work, portal/status, results communication | Consent and direct relationship with provider | Credit Connect says client is billed directly and no commission; Credit Logistic advertises no setup/minimum but compensation is disclosed during onboarding; CRE publishes $50/$150/$400 one-time commissions by program | Lowest operational and data burden; quick learning | Less control, weaker margin, provider owns relationship, referral/compensation rules require review |
| Hybrid | GoClear owns education, readiness assessment, relationship, funding re-entry, and service-quality oversight | Specialist owns regulated dispute execution, bureau communications, case evidence, and operational SLA | Same truthful documents/consent | Quote-based; model economics depend on GoClear service fee and vendor cost, which are currently unknown | Best balance of client continuity and specialist execution | Highest coordination and role-boundary risk; must not make GoClear the de facto unlicensed CSO |

## Provider shortlist and evidence matrix

Public statements below are **SOURCE CLAIMS**, not Nexus approvals. Prices and
service levels must be confirmed in a written proposal and contract.

| Candidate | Model / services | Customer ownership and communication | Public pricing / setup / timing | Data, portal, integration | State / compliance / reputation signal | Current assessment |
|---|---|---|---|---|---|---|
| **Credloom** | Direct credit-restoration service; public tiers cover 2 or 3 bureaus, dispute-volume limits, monitoring and escalation | Provider appears to contract/bill client; Partner+ advertises full white-label portal; partner page also describes read-only/co-branded options | Essentials $59/mo, Restoration $89/mo, Partner+ $149/mo; $0 upfront; billed monthly in arrears; public 30-day FCRA SLA with escalation ranges; no setup fee shown | Public privacy page says it collects name/contact, three reports, and tokenized payment data; public site advertises case-file/audit trail, client portal, written cancellation; API/webhook terms and subprocessors still need diligence | Public site presents CROA-conformed controls, no guarantees, 5-year case retention; public reputation sample is too thin to treat as established independent proof | **White-label / direct-service candidate for diligence**, not yet approved. Verify legal entity, registration/bonds, insurance, security, dispute methodology, state map, refunds, and actual fulfillment staffing |
| **The Credit Connect** | Direct credit education/dispute-assistance service; provider says it handles work and returns client when ready to transact | Referral partner sends consented client; provider contacts client; claims milestone updates and reciprocal return; no referral commission | Client pricing public by plan/case complexity but exact price not displayed on partner page; no upfront charges stated; claims meaningful improvement 60–120 days and typical completion within 6 months | Secure client portal; provider asks for permission before contacting client; warns not to email SSN/full reports/IDs; milestone visibility | Claims all-50-state acceptance and state registration where required; those claims require independent state-by-state verification. BBB page for similarly named Credit Connect Solutions is not enough to establish this entity’s standing; Trustpilot showed 6 reviews / 4.2 at capture | **Referral-first candidate** with good boundary clarity; verify entity identity, state registrations, pricing, complaints, insurance, data deletion, and SLA |
| **Credit Logistic** | Done-for-you referral partner focused on credit improvement/mortgage readiness | Provider says it guides client, gives high-level updates/readiness alerts, keeps sensitive reports from referring partner, and offers tracking portal | No minimum volume and no setup fees publicly stated; compensation and pricing are disclosed during onboarding; no per-client price public | Secure partner hub, milestone visibility, client portal, standardized communications; no API claim verified | Provider says structures align with applicable law; no independent licensing/reputation evidence verified in this pass | **Referral candidate**, especially mortgage-readiness use cases; verify actual dispute scope vs education, state coverage, compensation legality, security, and vendor continuity |
| **Credit Repair Evolved** | Provider performs all credit-repair services; affiliate program, not white-label fulfillment | Agreement says referred clients are CRE’s clients; partner cannot charge or advise on specific disputes; provider owns service | Published one-time commissions: $400 / $150 / $50 by program; commission only after start payment; chargeback/cancellation clawback; no minimum or exclusivity | Partner portal/tracked links; partner may not collect SSN, full account numbers, or report credentials | Agreement contains no-result/score/timeline-claim rules, FTC disclosure, consent, TCPA/CAN-SPAM restrictions; California entity/choice-of-law claim needs diligence | **Referral/affiliate candidate only**. Compensation and advertising rules require legal review before use; not a fit for a GoClear white-label promise without a new agreement |
| **Credence Credit** | Credit-repair CRM/platform; white-label/reseller, referral and technology-partner models; REST API/webhooks advertised | GoClear could own client relationship under a reseller model, but Credence is software, not proven dispute fulfillment | Partner page advertises 20% recurring commission for referrals; white-label pricing is not public; API pricing/limits not verified | Full API, webhooks, white-label portal, custom onboarding, support advertised | Platform claims are vendor claims; no fulfillment staffing, state registration, dispute SLA, insurance, or independent reputation was verified | **Technology / white-label platform candidate**, not a fulfillment provider. Use only if GoClear chooses to staff/contract actual dispute operations separately |
| **Credit Repair Cloud** | Software only; workflow, client billing, private-label portal, automations/API | GoClear would operate the service and own client relationship; vendor explicitly says it is software only | Public plans: $179/$299/$399/$599 monthly tiers (annual prices also shown), with 30-day trial; client/seat limits vary | Private-label portal, email automation, storage, API; terms restrict API to the subscriber’s data and prohibit using it for benchmarking the service | Vendor reports encrypted storage and daily backups; those claims require current security/DPA review; software does not solve licensing/fulfillment | **Build-enablement software**, not an outsourcing answer. Not recommended as first model while GoClear lacks a proven compliant operator |
| **The CRO Connect** | Publicly advertises outsourced dispute processing with creditors, collectors and bureaus | Likely B2B outsourcing; client ownership, portal/API, pricing, state scope and contractual terms not published | Quote/call required; no public minimum, per-client cost, or SLA found | Service page claims operational outsourcing but no verifiable API/security/deletion contract found | Self-described expertise only; no independent reputation or licensing proof verified | **Secondary diligence lead**, not shortlist-approved until contract/security/state evidence is obtained |

Excluded from recommendation: **Lexington Law / CreditRepair.com** due to the
CFPB enforcement record above, regardless of historical market scale.

## Responsibilities and handoff design

### GoClear

- Explain that credit repair cannot remove accurate, current negative data and
  cannot guarantee a score, deletion, funding, or approval outcome.
- Provide funding-readiness education and a non-diagnostic handoff summary.
- Obtain explicit, state-appropriate consent before sharing any referral data.
- Keep the funding objective and client relationship separate from provider
  dispute decisions.
- Receive only minimum necessary status events: referral accepted, intake
  complete, cycle started, client paused/cancelled, evidence/result ready,
  return-to-funding-ready signal.
- Never write dispute reasons, promise results, or direct a client to dispute
  accurate information unless counsel-approved education supports it.

### Outsource provider

- Own consumer contract, disclosures, cancellation, billing, dispute
  substantiation, bureau/furnisher communications, evidence, complaints,
  security, state compliance, and client-service SLA.
- Return a case-status packet without exposing unnecessary report contents.
- Provide breach notification, data deletion/return, subcontractor, retention,
  insurance, complaint, and business-continuity commitments.

### Nexus / Clyde

- Store the vendor-neutral provider profile, contract evidence, state map,
  service claims, source dates, and uncertainty.
- Match an internal non-PII profile to a service category; do not select or
  enroll a real client automatically.
- Flag missing state/licensing/data evidence and route bounded Research
  follow-ups.
- Keep lender/funding qualification separate from credit-repair claims.

### Client

- Decide whether to contact/enroll after receiving disclosures.
- Give truthful, complete documents and dispute basis directly through the
  provider’s secure intake.
- Authorize any report access and understand cancellation, billing,
  communication, and no-guarantee terms.

## Recommended next internal test

Use a **non-PII synthetic profile** and compare the referral-first and hybrid
operating contracts without contacting a provider:

1. Build a state matrix for GoClear’s actual target states.
2. Request written diligence packets from at least Credloom, The Credit
   Connect, and Credit Logistic only after Ray approves outreach.
3. Score each against compliance, state authority, client ownership, data
   minimization, portal/status evidence, SLA, complaint history, refund terms,
   business continuity, and total economics.
4. Simulate referral → provider intake → milestone update → return to Clyde
   using no PII and no external submission.
5. Have counsel review the chosen role/compensation/marketing structure before
   any customer-facing use.

## Due-diligence questions before any agreement

1. What legal entity contracts with the consumer, in each target state?
2. Which CSO registrations, licenses, bonds, surety accounts, or exemptions
   apply, and can the provider produce current evidence?
3. Who writes and signs the consumer contract, disclosures, cancellation notice,
   and refund policy?
4. Exactly when may any fee be requested or collected, including telemarketing
   or affiliate channels?
5. Which services are actually performed: report review, dispute preparation,
   furnisher contact, bureau follow-up, identity-theft work, education, or
   monitoring?
6. What substantiation is retained for every dispute, and can the client obtain
   it?
7. What states, client types, languages, and report conditions are excluded?
8. Who owns the customer, the case file, the portal account, and the data after
   cancellation or termination?
9. Is white-label branding permitted without obscuring the actual provider and
   legal disclosures?
10. What is the exact pricing: setup, per-client, recurring, bureau/report,
    escalation, cancellation, refund, chargeback, and minimum volume?
11. What turnaround is contractual versus marketing language? What happens if
    the provider misses an SLA?
12. What secure intake, encryption, access logging, retention/deletion,
    subcontractor, breach-notification, and disaster-recovery controls exist?
13. What API/webhook/portal events are available, and can GoClear receive only
    high-level status rather than full reports?
14. What independent complaints, enforcement, litigation, insurance, and
    references can be reviewed?
15. May the provider market loans, cards, or other products to GoClear clients?
16. What happens to open cases, payments, and client data if the provider
    closes, is terminated, or loses a required registration?

## Human decisions required from Ray

- Identify GoClear’s intended operating states and whether it will market,
  contract, receive compensation, or merely refer.
- Choose whether the first test should be referral-first or a counsel-approved
  hybrid.
- Approve any provider outreach or submission of even basic lead/contact data.
- Decide whether GoClear wants referral revenue; compensation can change the
  legal and advertising analysis.
- Approve counsel/vendor-diligence budget if any; no spend has been made.
- Approve customer-facing wording only after compliance review.

## Final disposition

`RESEARCH_MORE` → **bounded vendor/state due diligence required**.

The evidence supports a referral-first/hybrid hypothesis, but it does not
support selecting a provider, claiming nationwide coverage, setting a price,
or making a customer-facing recommendation. The next owner is `CLYDE_CREDIT`
for internal comparison; any external contact or client action remains a Ray
approval boundary.

## Source register

- [CFPB: credit-repair scams and counselor guidance](https://www.consumerfinance.gov/ask-cfpb/how-can-i-tell-a-credit-repair-scam-from-a-reputable-credit-counselor-en-1343/)
- [FTC: credit-repair scam warning](https://consumer.ftc.gov/consumer-alerts/2026/01/spot-scams-when-fixing-your-credit)
- [California DOJ: CSO registration](https://oag.ca.gov/node/22352)
- [Texas Secretary of State: CSO FAQ](https://www.sos.state.tx.us/statdoc/faqs2800.shtml)
- [CFPB: Lexington Law / CreditRepair.com enforcement](https://www.consumerfinance.gov/enforcement/payments-harmed-consumers/payments-by-case/lexlaw/)
- [Credloom pricing](https://www.getcredloom.com/pricing), [privacy](https://www.getcredloom.com/privacy)
- [The Credit Connect partner program](https://partners.getcreditconnect.com/), [contact/security notice](https://getcreditconnect.com/contact)
- [Credit Logistic partner hub](https://go.creditlogistic.com/)
- [Credit Repair Evolved affiliate policy](https://creditrepairevolved.co/affiliate-policy/)
- [Credence Credit partner program](https://credence.credit/partners)
- [Credit Repair Cloud pricing](https://www.creditrepaircloud.com/pricing), [API restrictions](https://www.creditrepaircloud.com/apirestrictions)
- [The CRO Connect outsourcing page](https://www.thecroconnect.com/)
