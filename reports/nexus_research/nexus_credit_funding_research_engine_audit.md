# Nexus Credit & Funding Research Engine Audit

**Generated**: 2026-07-03  
**Scope**: Existing credit, funding, business setup, and GoClear research in nexus-os-v2  
**Status**: Comprehensive — significant existing assets found

---

## 1. What credit/funding research files already exist?

### Core Business Logic (src/)
| File | Content |
|------|---------|
| `src/data/creditFundingData.js` | Demo credit data model: score factors, dispute drafts, fundability checklist, bankability items, utilization gaps |
| `src/data/clientPortalData.js` | Fundability checklist, credit monitoring, business profile, funding readiness UI data |
| `src/lib/clientWorkflowEngine.ts` | Credit scoring engine: utilization, collections, charge-offs, late payments, inquiries, bankability |
| `src/lib/clientWorkflowHermes.ts` | Hermes credit/funding recommendations: stuck clients, credit report pending, mailing gaps |
| `src/lib/readinessReviewIntake.ts` | 16-section intake template including credit_utilization, credit_negative_items, business_profile |
| `src/lib/readinessReviewScorecard.ts` | 8-section manual scoring with utilization tiers (70/50/30/10%) |
| `src/lib/readinessReviewReportDraft.ts` | Report draft generator with credit findings, utilization, business setup, funding recommendations |
| `src/lib/nexusReadinessRegistry.ts` | Readiness registry tracking credit, funding, and business setup areas |
| `src/lib/hermesLocalOperatingCommands.ts` | 25+ operating questions including credit repair, funding readiness, $97 review |
| `src/lib/creditSpecialistPolicy.ts` | Credit specialist access contract: mock data only, compliance language |
| `src/config/clientWorkflow.ts` | 17 workflow stages, 7 dispute letter types, mailing methods, LLC/EIN/DUNS/NAICS items |
| `src/config/clientWorkflowAffiliate.ts` | 12 affiliate categories mapped to credit/funding workflow tasks |
| `src/config/partnerOffers.ts` | 15+ partner offers with affiliate/referral revenue types |
| `src/config/onlineBusinessBankAffiliates.ts` | 7 bank affiliate research: Bluevine, Mercury, Relay, Novo, Found, North One, Lili |
| `src/config/goclearSubscriptionTiers.ts` | 4 subscription tiers ($49-$197/mo) |
| `src/config/nexusRevenueStreams.ts` | Revenue streams: readiness review, subscription, affiliate, funding commission |
| `src/config/nexusApprovedKnowledge.ts` | FCRA dispute basics knowledge record |

### Reports (reports/)
| Report | Content |
|--------|---------|
| `reports/nexus_readiness/credit_repair_operating_readiness.md` | **FULL 186-line audit**: scoring engine, dispute workflow, client portal, gaps, missing items |
| `reports/nexus_readiness/business_funding_operating_readiness.md` | **FULL 190-line audit**: business setup 13 items, bankability scoring, funding paths, gaps |
| `reports/nexus_readiness/readiness_review_client_intake.md` | Full client intake template |
| `reports/nexus_readiness/readiness_review_scorecard.md` | Manual scorecard with all sections |
| `reports/nexus_readiness/readiness_review_client_report_template.md` | Client report template |
| `reports/nexus_readiness/readiness_review_admin_fulfillment_checklist.md` | Fulfillment checklist |
| `reports/nexus_readiness/readiness_review_manual_launch_plan.md` | Step-by-step manual launch plan |
| `reports/nexus_readiness/readiness_review_offer_audit.md` | Offer audit with scoring |
| `reports/goclear_activation/goclear_credit_funding_activation_audit.md` | **FULL activation audit**: what exists, what's active, what's blocked |
| `reports/goclear_activation/goclear_launch_readiness_report.md` | Launch readiness report |

### Configs (configs/)
| Config | Content |
|--------|---------|
| `configs/dispute_simulation_cases.json` | 5 dispute simulation cases |
| `configs/specialist_personality_profiles.json` | Credit/funding specialist profiles |
| `configs/specialist_registry.json` | Specialist roles including funding |
| `configs/offer_registry.json` | 9 offers targeting fundability |
| `configs/research_discovery_topics.json` | Credit repair, business funding, grants topics |

### Scripts (scripts/)
| Script | Content |
|--------|---------|
| `scripts/compliance/classify_claim_risk.py` | Credit repair compliance classification |
| `scripts/disputes/run_dispute_simulation_lab.py` | End-to-end synthetic dispute pipeline |
| `scripts/client_flow/common.py` | Credit/funding client tasks |

### Public
| File | Content |
|------|---------|
| `public/goclear-apex-readiness.html` | **Full $97 readiness review landing page** with features, FAQ, pricing, CTA |

---

## 2. What reports already exist?

**21+ credit/funding/GoClear reports** across three directories:

- `reports/nexus_readiness/` — 16 files (heaviest: credit repair audit, business funding audit, intake, scorecard, report template, launch plan)
- `reports/goclear_activation/` — 4 files (activation audit, launch readiness, marketing activation, process results)
- `reports/manual_publish/` — 7+ files (credit repair workflow, funding readiness, client flows, specialist contract)

**No credit/funding research exists in `hermes_alpha/`** — it is purely business opportunity/marketing research.

---

## 3. What GoClear readiness workflows already exist?

| Workflow | Status | Location |
|----------|--------|----------|
| $97 Readiness Review intake | Real, 15 sections, mounted at `#readiness-intake` | `src/components/ReadinessReviewIntake.jsx` |
| $97 Readiness Review admin | Real, 4 tabs, mounted at `#readiness-admin` | `src/components/ReadinessReviewAdmin.jsx` |
| Scorecard (8 sections, 5 tiers) | Real, deterministic | `src/lib/readinessReviewScorecard.ts` |
| Report draft generator | Real, 9 sections + disclaimer | `src/lib/readinessReviewReportDraft.ts` |
| Credit analysis scoring engine | Real, functional | `src/lib/clientWorkflowEngine.ts` |
| Bankability scoring | Real, 13 items | `src/lib/clientWorkflowEngine.ts` |
| Funding readiness scoring | Real, combines credit + business | `src/lib/clientWorkflowEngine.ts` |
| Dispute simulation lab | Real, 5 cases | `scripts/disputes/run_dispute_simulation_lab.py` |
| Client portal (credit repair page) | Real React, static demo | `src/pages/client/ClientPortalPages.jsx` |
| Client portal (funding readiness page) | Real React, static demo | `src/pages/client/ClientPortalPages.jsx` |
| $97 landing page | Real HTML | `public/goclear-apex-readiness.html` |

---

## 4. What affiliate/referral ideas already exist?

| Affiliate Category | Partners | Status |
|--------------------|----------|--------|
| Business bank accounts | Bluevine, Mercury, Relay, Novo, Found, North One, Lili | Research exists, URLs null, not applied |
| Credit monitoring | SmartCredit, IdentityIQ | Config exists, not activated |
| LLC/Entity formation | Formation.com | Config exists, URL null |
| Registered agent | ZenBusiness | Config exists, URL null |
| Mailing/DocuPost | DocuPost | Config exists, URL null |
| Business phone | Grasshopper | Config exists, URL null |
| Website/Domain | Various | Config exists, URLs null |
| Bookkeeping | QuickBooks | Config exists, URL null |

**All 13 partner programs show `not_applied` status** in `affiliateApprovalStatus.ts`.

---

## 5. What research is missing?

### Critical Gaps
1. **FDCPA references** — Zero matches despite credit repair focus. FCRA exists (4 matches) but FDCPA is absent.
2. **Actual research artifacts** — Config/reports define structure but no collected research (lender criteria, grant databases, compliance notes, etc.)
3. **Grant research** — Only structural references, no actual grant databases or programs researched
4. **Lender research** — No actual lender criteria, underwriting requirements, or program details collected
5. **Credit repair education** — No client-facing educational content beyond disclaimers
6. **Business setup guides** — No step-by-step guides for LLC, EIN, DUNS, NAICS registration
7. **Dispute compliance notes** — No FCRA/FDCPA compliance education beyond basic knowledge record
8. **Utilization improvement recommendations** — Scorecard tiers exist but no research-backed improvement strategies
9. **Fundability checklist research** — Structure exists but no research on what actually improves fundability

### Already Designed But Not Implemented
- Marketing dept design (in `hermes_alpha/`)
- Business opportunity desk (in `hermes_alpha/`)
- Affiliate offer lab (in `hermes_alpha/`)
- Vibe-trading adapter (in `hermes_alpha/`)

---

## 6. What should be Nexus-owned instead of Alpha-owned?

| Asset | Current Owner | Recommended Owner | Reason |
|-------|---------------|-------------------|--------|
| Credit repair research | Neither | **Nexus** | Client-facing, compliance-sensitive |
| Credit utilization research | Neither | **Nexus** | Directly affects client scoring |
| Business funding research | Neither | **Nexus** | Client-facing, approval-gated |
| Grant research | Neither | **Nexus** | Client-facing opportunity |
| Lender research | Neither | **Nexus** | Admin-only, compliance-sensitive |
| Compliance notes | Neither | **Nexus** | Required for client safety |
| Client education | Neither | **Nexus** | Client-facing |
| Fundability checklist | Nexus (structure) | **Nexus** | Already Nexus-owned |
| Affiliate offers | Both | **Nexus** (credit/funding specific) | Client workflow integration |
| Business opportunity research | Alpha | **Alpha** | Not client-facing |
| Marketing research | Alpha | **Alpha** | Not client-facing |
| Trading research | Alpha | **Alpha** | Not client-facing |
| AI tools/repos | Alpha | **Alpha** | Not client-facing |

---

## 7. What should require Ray Review?

| Item | Ray Review Required | Reason |
|------|---------------------|--------|
| Any credit repair recommendation | Yes | Compliance, legal exposure |
| Any funding recommendation | Yes | Financial advice implications |
| Any lender referral | Yes | Financial advice implications |
| Any grant recommendation | Yes | Must verify legitimacy |
| Any dispute letter content | Yes | FCRA compliance |
| Any client-facing education | Yes | Accuracy, compliance |
| Any affiliate promotion | Yes | FTC disclosure requirements |
| Any compliance note update | Yes | Legal implications |
| Any fundability score change | Yes | Affects client decisions |
| Any business setup recommendation | Yes | Legal/tax implications |

---

## 8. What should be client-facing vs admin-only?

### Client-Facing (After Approval)
- Credit utilization education (general, not specific advice)
- Business setup checklist overview
- Fundability checklist overview
- $97 review report (after Ray Review)
- Credit monitoring options (general)
- Business bank account options (general)
- Grant opportunity overview (general)

### Admin-Only (Ray/Internal)
- Lender matching notes
- Dispute strategy recommendations
- Funding application preparation
- Compliance audit notes
- Affiliate offer evaluation
- Credit report analysis details
- Business profile scoring details
- Specialist handoff drafts

---

## 9. What should remain manual for now?

| Activity | Why Manual |
|----------|------------|
| Credit report collection | No secure upload/storage |
| Credit analysis entry | No live SmartCredit integration |
| Dispute letter drafting | No bureau/creditor connectors |
| Mailing physical letters | No DocuPost/USPS integration |
| Funding applications | No lender integrations |
| DUNS registration | No Dun & Bradstreet integration |
| EIN/LLC verification | No SOS integration |
| Business bank account setup | No bank API integration |
| Grant applications | No grant database integration |
| Email/follow-up | No Resend integration |
| Specialist assignment | No live specialist agents |
| Payment collection | No production Stripe |

---

## Summary

| Category | Status |
|----------|--------|
| Existing credit/funding code | Extensive — scoring engine, workflow, config, UI |
| Existing reports | 21+ across nexus_readiness, goclear_activation, manual_publish |
| GoClear readiness workflows | $97 review fully scaffolded (intake, admin, scorecard, report draft) |
| Affiliate/referral research | 7 bank affiliates researched, 13 partner programs tracked, all `not_applied` |
| Missing research | FDCPA, grant databases, lender criteria, utilization strategies, client education |
| Nexus-owned assets | Credit, funding, compliance, client education — all should be Nexus-owned |
| Alpha-owned assets | Business opportunity, marketing, trading, AI tools — remain Alpha-owned |
| Manual items | All external integrations remain manual until connectors built |
