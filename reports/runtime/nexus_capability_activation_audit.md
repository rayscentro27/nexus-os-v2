# Nexus Capability Activation Audit

**Generated**: 2026-07-05

---

## Capability List by Department

### Marketing/Funnel

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| Got Funding landing page | Built, deployed, form works | 85 | APPROVED_LIVE | `reports/marketing_assets/`, `tests/got_funding_*.test.ts` |
| QR funnel | QR code generation exists | 50 | DRY_RUN | `scripts/generate_got_funding_qr.swift` |
| Netlify lead capture | Form submission configured | 75 | SANDBOX_TEST | Netlify functions, `netlify.toml` |
| Thank-you route | Exists in Got Funding | 70 | SANDBOX_TEST | Route tested |
| Landing page builder quality | Premium standard established | 80 | OBSERVE | Got Funding as benchmark |
| Affiliate links | Config files exist | 30 | OBSERVE | `configs/offer_registry.json` |
| Email sending | Resend configured | 40 | DRY_RUN | `RESEND_API_KEY` in `.env` |
| Social/video posting | Meta integration configured | 35 | DRY_RUN | Meta tokens in `.env` |
| TikTok posting | Not built | 0 | N/A | No code found |
| YouTube channel/content workflow | Research scripts exist | 45 | DRY_RUN | `scripts/research/` |

### Research

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| YouTube researcher | Scripts + cache exist | 55 | DRY_RUN | `data/cache/youtube/`, `scripts/research/` |
| NotebookLM export/import | Export bundles exist | 40 | OBSERVE | `data/exports/notebooklm/` |
| Research-to-money pipeline | Report exists | 35 | OBSERVE | `reports/manual_publish/research_to_money_pipeline_latest.md` |
| External URL review | Netlify function exists | 60 | SANDBOX_TEST | `netlify/functions/alpha-url-review.mjs` |
| GitHub repo review | Not built | 0 | N/A | No code found |
| Independent YouTube/video review | Alpha has foundation | 30 | OBSERVE | `src/hermes/alpha/alphaUrlReview.ts` |
| Opportunity scoring | Alpha scoring exists | 50 | DRY_RUN | `src/hermes/alpha/alphaScoring.ts` |
| Report generation | Multiple generators | 65 | DRY_RUN | `scripts/reports/` |

### Alpha/Nexus Brains

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| Alpha strategy brain | Core engine built | 60 | SANDBOX_TEST | `src/hermes/alpha/alphaBrain.ts` |
| Alpha provider routing | Multi-provider router | 55 | SANDBOX_TEST | `src/hermes/alpha/alphaProviderRouter.ts` |
| Alpha URL review foundation | Netlify function + code | 60 | SANDBOX_TEST | `netlify/functions/alpha-url-review.mjs` |
| Alpha independent research intake | Framework exists | 35 | OBSERVE | `src/hermes/alpha/alphaResearchFileAdapter.ts` |
| Alpha report-context readiness | Adapter exists | 40 | OBSERVE | `src/hermes/alpha/alphaResearchFileAdapter.ts` |
| Nexus Hermes operations brain | Extensive codebase | 70 | SANDBOX_TEST | `src/hermes/nexus/` (11 files) |
| Nexus Hermes prompt-to-process routing | Intent classifier built | 55 | DRY_RUN | `src/lib/hermesIntentClassifier.ts` |
| Ray Review/Approvals | UI + queue exists | 65 | OBSERVE | `src/components/RayReviewCenter.jsx` |

### Client Portal

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| Onboarding | Shell exists | 40 | OBSERVE | `src/components/client/ClientPortalShell.jsx` |
| Credit profile | Placeholder data | 25 | OBSERVE | `src/data/creditFundingData.js` |
| Credit utilization | Not connected | 20 | OBSERVE | No real data path |
| Business setup profile | Migration exists, no UI | 30 | OBSERVE | Migration 20260629090000 |
| Business bankability | Not built | 15 | N/A | No code found |
| Funding readiness | Migration exists | 30 | OBSERVE | Migration 20260629095450 |
| Documents | Migration exists, no UI | 25 | OBSERVE | `client_documents` table |
| Recommendations | Placeholder | 20 | OBSERVE | `src/data/clientPortalData.js` |
| Resources/affiliate options | Config exists | 25 | OBSERVE | `configs/offer_registry.json` |
| Request review/next step | Not built | 15 | N/A | No code found |

### Credit/Funding

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| Credit report upload | Not built | 0 | N/A | No upload mechanism |
| Local/private report processing | Not built | 0 | N/A | No processing code |
| Credit plan generation | Not built | 0 | N/A | No generation code |
| Dispute letter draft generation | Migration exists | 20 | OBSERVE | `dispute_letter_drafts` table |
| Utilization recommendation | Not built | 0 | N/A | No recommendation engine |
| Business setup checklist | Migration exists | 25 | OBSERVE | `business_setup_items` table |
| Business bank account readiness | Not built | 0 | N/A | No code found |
| Credit card offer research | Not built | 0 | N/A | No research code |
| Grant research | Seed data exists | 15 | OBSERVE | `nexus_research/grants/` |
| Grant application draft package | Not built | 0 | N/A | No generation code |

### Trading

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| Trading idea research | Alpha pipeline exists | 45 | DRY_RUN | `src/hermes/alpha/alphaTradingResearchPipeline.ts` |
| Strategy creation | Not built | 10 | N/A | No strategy builder |
| Money management rules | Config exists | 25 | OBSERVE | `configs/oanda_demo_trading_policy.json` |
| Backtest | Backtest data exists | 35 | OBSERVE | `reports/runtime/backtests/` |
| Strategy comparison/tournament | Report exists | 40 | DRY_RUN | `reports/manual_publish/trading_demo_tournament_latest.md` |
| Oanda demo trade proof | Scripts exist | 45 | SANDBOX_TEST | `scripts/trading/` |
| Live trading readiness | Blocked by design | 15 | N/A | `LIVE_TRADING=false` |

### Billing/Referral

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| Stripe/customer billing | Config exists | 30 | OBSERVE | `configs/stripe_product_registry.json` |
| Subscriptions | Migration exists | 25 | OBSERVE | `subscription_memberships` table |
| Referral tracking | Not built | 0 | N/A | No tracking code |
| Referral payout calculation | Not built | 0 | N/A | No calculation code |
| Synthetic referral test | Not built | 0 | N/A | No test code |

### System

| Capability | Status | Score | Mode | Evidence |
|-----------|--------|-------|------|----------|
| Command Center | UI exists, data is mock | 50 | OBSERVE | `src/components/CommandCenter.jsx` |
| System Health | Panel exists, data is mock | 45 | OBSERVE | `src/components/SystemHealthPanel.jsx` |
| Process registry | Config exists | 55 | OBSERVE | `configs/automation_schedule_registry.json` |
| Report index | Generated | 60 | OBSERVE | `reports/manual_publish/report_registry_latest.md` |
| Connector registry | Config exists | 50 | OBSERVE | `configs/connector_registry.json` |
| Automation/scheduler/cron | LaunchD configured | 45 | SANDBOX_TEST | `ops/launchd/` |
| Kill switches | Policy exists | 40 | OBSERVE | `src/config/nexusActionPolicy.ts` |
| Cost controls | Alpha cost controller | 45 | OBSERVE | `src/hermes/alpha/alphaCostController.ts` |
| Route/page inventory | Comprehensive | 65 | OBSERVE | `src/data/nexusNavigationConfig.js` |
