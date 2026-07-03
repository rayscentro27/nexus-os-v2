# Business Funding Operating Readiness Audit

**Date:** 2026-07-02
**Scope:** Nexus OS business funding workflow — full readiness audit
**Status:** Partial — engine and config ready, live integrations blocked

---

## 1. What Exists Now

| Component | Status | Source |
|---|---|---|
| Business setup item model (13 items) | Real config | `src/config/clientWorkflow.ts` — LLC, EIN, registered agent, business address, business phone, website/domain/email, DUNS, business bank account, bookkeeping, vendor accounts, licenses/permits, bank statements |
| Bankability scoring engine | Real code | `src/lib/clientWorkflowEngine.ts` — `scoreBankability()` with per-item score impacts |
| Funding readiness scoring | Real code | `src/lib/clientWorkflowEngine.ts` — `fundingReadinessScore()` combines credit + business |
| Affiliate recommendation mapping (12 categories) | Real config | `src/config/clientWorkflowAffiliate.ts` — credit monitoring, formation, registered agent, address, phone, website, credit profile, bank account, bookkeeping, vendor accounts, mailing, funding services |
| Partner offer registry (15 partners) | Real config | `src/config/partnerOffers.ts` — SmartCredit, Bluevine, Mercury, Relay, Formation, DocuPost, etc. |
| Revenue streams model (4 streams) | Real config | `src/config/nexusRevenueStreams.ts` — readiness review, monthly subscription, affiliate engine, funding commission |
| Subscription tiers (4 GoClear tiers) | Real config | `src/config/goclearSubscriptionTiers.ts` — $49, $97, $197, $149/mo |
| Offer registry (9 offers) | Real config | `configs/offer_registry.json` — $97 through $497, monthly, grants, checklist |
| Online bank affiliate research (7 banks) | Real config | `src/config/onlineBusinessBankAffiliates.ts` — Bluevine, Mercury, Relay, Novo, Found, North One, Lili |
| Affiliate approval status tracking | Real config | `src/config/affiliateApprovalStatus.ts` — 13 partner programs, all `not_applied` |
| Client workflow monetization mapping | Real code | `src/lib/clientWorkflowMonetization.ts` — 15 tasks mapped to revenue paths |
| Client portal UI (FundingReadinessPage) | Real React | `src/pages/client/ClientPortalPages.jsx` — fundability checklist, funding paths, blocker groups |
| Supabase schema (24 tables) | Real SQL | `supabase/migrations/20260629095450_client_portal_core_tables.sql` — business_profile_requirements, funding_readiness_scores, partner_offers |
| Payment infrastructure (Stripe) | Real config | `configs/stripe_product_registry.json` — $97 test checkout open, rest draft |
| Payment-to-onboarding flow | Real script | `scripts/payments/prepare_payment_to_client_onboarding_flow.py` — 8-step post-payment pipeline |
| Public landing page | Real HTML | `public/goclear-apex-readiness.html` — $97 readiness review marketing page |

---

## 2. What Is Connected

| Connection | Status |
|---|---|
| Hermes can read funding readiness score | Partial — static demo data only |
| Hermes can detect missing business setup items | Yes — via `clientWorkflowEngine.ts` scoring |
| Hermes can recommend affiliate partners | Yes — config exists, all URLs null |
| Hermes can prepare Ray Review drafts for funding decisions | Yes — via `approval_action_prepare` route |
| Stripe test checkout for $97 | Open — test mode only |
| Client portal renders funding readiness page | Yes — static demo data |
| Revenue projections modeled | Yes — conservative/realistic/stretch scenarios |
| Offer ladder defined | Yes — $97 → $297 → $497 → monthly |

---

## 3. What Is Only Placeholder/Static

| Component | Nature |
|---|---|
| All affiliate URLs | `null` — no partner programs applied to |
| Client portal data | `demo_only: true` — no real client data |
| Business setup checklist | Static demo items — no live tracking |
| Funding readiness score | Static demo (58/100) — no live computation |
| Partner offers | All `proposed` / `needs_config` status |
| Revenue projections | Estimated — `currentMonthlyRevenue: 0` across all streams |
| Business opportunities | 26 scored candidates — no live connections |
| Marketing drafts | 10+ drafts — none published |
| Subscription engine | Config only — no live billing |
| Business bank account integration | Research only — no live API |
| Tradeline/vendor account logic | Concept only — no implementation |
| NAICS code lookup | Checklist item only — no lookup table |
| SOS filing integration | DIY option text only — no integration |

---

## 4. What Hermes Can Read

| Data | Access |
|---|---|
| Business setup item definitions | Yes — 13 items with score impacts |
| Funding readiness score (static) | Yes — `creditFundingData.fundingReadiness.score` (hardcoded 58) |
| Bankability checklist items | Yes — static demo |
| Partner offer definitions | Yes — 15 partners with categories |
| Subscription tier definitions | Yes — 4 tiers with pricing |
| Revenue stream projections | Yes — estimated ranges |
| Affiliate approval status | Yes — all `not_applied` |
| Funding path options | Yes — credit union, business card, community bank, SBA |

---

## 5. What Hermes Cannot Read

| Data | Reason |
|---|---|
| Real client business profiles | No live client database |
| Live DUNS registration status | No Dun & Bradstreet integration |
| Live EIN/LLC filing status | No Secretary of State integration |
| Live bank account status | No bank API integration |
| Live vendor credit line status | No tradeline monitoring |
| Live funding application status | No lender integrations |
| Real fundability scores | No live computation on real data |
| Grant database | No live grant API |
| Partner application status | All `not_applied` |

---

## 6. What the Client Can Do

| Action | Status |
|---|---|
| View funding readiness page | Yes — static demo at `/client/funding-readiness` |
| See fundability checklist | Yes — 11 demo items |
| See funding path options | Yes — 4 demo paths with fit scores |
| See blocker groups | Yes — demo blockers |
| See document checklist | Yes — 10 demo items |
| See partner offers | Yes — demo partner list |
| Apply for funding | No — no lender integrations |
| Open business bank account | No — affiliate URLs null |
| Register for DUNS | No — no integration |
| Track setup progress | No — checklist is static |

---

## 7. What Admin/Ray Can Do

| Action | Status |
|---|---|
| View funding readiness status | Yes — via demo data |
| Review business opportunity rankings | Yes — 26 scored candidates |
| Create Ray Review cards for funding decisions | Yes — via pipeline |
| Prepare specialist handoff for funding | Yes — conversation-only draft |
| Run payment readiness contract | Yes — Python script |
| Prepare Stripe test checkout | Yes — script exists |
| Review affiliate opportunity tracker | Yes — Python script |
| Generate revenue launch review cards | Yes — Python script |

---

## 8. What Is Missing Before Real Client Use

| Gap | Impact | Priority |
|---|---|---|
| Live client database | No real client profiles | Critical |
| Business bank account integration | Cannot guide bank setup | Critical |
| EIN/LLC filing verification | Cannot verify entity status | Critical |
| DUNS registration integration | Cannot track DUNS progress | Critical |
| Live funding readiness scoring | Cannot compute real scores | High |
| Vendor/tradeline monitoring | Cannot track credit building | High |
| Lender matching engine | Cannot match clients to lenders | High |
| Grant database integration | Cannot detect grant opportunities | High |
| Affiliate link activation | Cannot earn referral revenue | High |
| Email/follow-up automation | No Resend integration | Medium |
| Client onboarding automation | Pipeline exists in scripts, not wired | Medium |
| Document management | No secure upload/download | Medium |
| Business credit monitoring | No tradeline or score tracking | Medium |

---

## 9. What Needs Approval Gates

| Item | Gate |
|---|---|
| Any funding application submitted | Ray Review approval required |
| Any lender referral | Ray Review approval required |
| Affiliate link activation | Affiliate approval required per `affiliateApprovalStatus.ts` |
| Client data exposure to funding specialist | Approval-gated |
| Business bank account recommendation | Ray Review approval required |
| Grant application assistance | Ray Review approval required |
| Any payment collection | Stripe checkout approval required |

---

## 10. Recommended Repair Order

1. **Live client database** — Apply Supabase migrations, create first test client
2. **Business profile intake** — Build LLC/EIN/address/phone collection flow
3. **DUNS registration guide** — Step-by-step DUNS setup with progress tracking
4. **Business bank account path** — Activate Bluevine affiliate, build onboarding guide
5. **Live funding readiness scoring** — Wire scoring engine to real client data
6. **Vendor credit account tracking** — Build tradeline monitoring model
7. **Lender matching** — Define criteria for credit union, business card, community bank, SBA paths
8. **Grant database** — Integrate grant opportunity detection
9. **Email/follow-up** — Resend integration for funding milestone notifications
10. **Funding application workflow** — Build application prep with approval gates

---

## Summary

| Aspect | Status |
|---|---|
| Business setup item model | Real, 13 items with score impacts |
| Funding scoring engine | Real, deterministic, functional |
| Affiliate/partner config | Real, all URLs null, not activated |
| Revenue model | Real, projected $0 actual |
| Client portal UI | Real React, static demo data |
| Live integrations | None — bank, DUNS, EIN, grant, lender all blocked |
| Safety guards | Strong — approval gates, affiliate disclosure |
| Production readiness | **Not ready** — no live clients, no live data, no external actions |
