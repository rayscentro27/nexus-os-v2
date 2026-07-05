# Nexus Capability Scorecard

**Generated**: 2026-07-05

---

## Score Legend

| Range | Classification |
|-------|---------------|
| 0-20 | Not built / placeholder |
| 21-40 | Exists but disconnected |
| 41-60 | Runs locally but not visible in Nexus |
| 61-80 | Usable in dry run or sandbox |
| 81-100 | Active and operational |

---

## Scorecard Summary

| Department | Capabilities | Avg Score | Highest | Lowest |
|-----------|-------------|-----------|---------|--------|
| Marketing/Funnel | 10 | 44 | 85 (Got Funding) | 0 (TikTok) |
| Research | 8 | 34 | 65 (Report gen) | 0 (GitHub review) |
| Alpha/Nexus Brains | 8 | 54 | 70 (Hermes ops brain) | 35 (Research intake) |
| Client Portal | 10 | 25 | 40 (Onboarding) | 15 (Request review) |
| Credit/Funding | 10 | 8 | 25 (Business checklist) | 0 (Multiple) |
| Trading | 7 | 31 | 45 (Oanda demo) | 10 (Strategy creation) |
| Billing/Referral | 5 | 11 | 30 (Stripe billing) | 0 (Multiple) |
| System | 10 | 51 | 65 (Route inventory) | 40 (Kill switches) |

---

## Top 5 Working Capabilities (Score 61+)

1. **Got Funding landing page** (85) — Deployed, form works, premium quality, APPROVED_LIVE
2. **Nexus Hermes operations brain** (70) — Extensive codebase, SANDBOX_TEST ready
3. **Thank-you route** (70) — Exists in Got Funding flow
4. **Ray Review/Approvals** (65) — UI + queue exists, data is local/mock
5. **Report generation** (65) — Multiple generators, DRY_RUN capable

## Top 5 Broken/Disconnected Capabilities (Score 0-20)

1. **Credit report upload** (0) — No upload mechanism
2. **Credit plan generation** (0) — No generation code
3. **Utilization recommendation** (0) — No recommendation engine
4. **Business bank account readiness** (0) — No code found
5. **Credit card offer research** (0) — No research code

## Capabilities Needing Supabase Verification

| Capability | Issue |
|-----------|-------|
| Client Portal (all steps) | Tables defined in migration but live data unverified |
| Department Feeders | Write paths defined but execution unverified |
| Process Registry | Config exists but live process status unknown |
| System Health | Panel exists but data source is mock |

---

## Overall System Readiness

| Category | Score | Assessment |
|----------|-------|------------|
| Code Foundation | 75 | Extensive codebase, well-structured |
| Live Data Connections | 35 | Most data is mock/local |
| Supabase Integration | 50 | Schema defined, writes via service role, live status unverified |
| External Connectors | 40 | Keys present, connections untested |
| UI/UX Quality | 55 | Got Funding is excellent, other pages need work |
| Brain Readiness (Alpha) | 50 | Core engine built, needs live data |
| Brain Readiness (Hermes) | 60 | Extensive routing, needs live context |
| Process Automation | 40 | Scripts exist, execution unverified |
| **Overall** | **46** | Foundation strong, activation needed |
