# GoClear Readiness Review — Internal Testing Plan

**Generated**: 2026-07-04

---

## Purpose

Design a safe internal testing plan for the $97 Credit & Funding Readiness Review using Nexus Research seed categories. All testing uses hypothetical/internal test profiles only.

**Hard rules for this plan:**
- No real clients
- No real client data
- No Supabase connection
- No approved client-facing advice
- No outcome guarantees
- All outputs draft-only and Ray Review-gated

---

## Test Profile Structure

Each hypothetical test profile should include:

```json
{
  "profile_id": "TEST-001",
  "profile_type": "hypothetical",
  "credit_utilization_pct": 45,
  "has_business_entity": true,
  "entity_type": "LLC",
  "time_in_business_months": 18,
  "annual_revenue": 85000,
  "existing_debt": 12000,
  "credit_score_range": "650-700",
  "funding_goal": "25000",
  "notes": "Hypothetical test profile for internal workflow testing"
}
```

**Input fields needed later (not connected now):**
- Credit utilization percentage
- Business entity status (LLC, Corp, Sole Prop, None)
- Time in business
- Annual revenue
- Existing debt levels
- Credit score range (general, not specific)
- Funding goal amount
- Industry/NAICS code

---

## Research Categories Used Per Workflow

### 1. Credit Utilization Review

| Research Category | Route | Use |
|-------------------|-------|-----|
| credit_utilization | scorecard_recommendation | Utilization ratio analysis, readiness scoring |

**Expected admin note output:**
- Summary of utilization readiness
- Scorecard input values
- Risk flags
- Recommended next steps (admin-only)

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for readiness assessment
- Why it matters for GoClear
- Client-facing status: no

**Blocked client-facing output:**
- Specific payoff advice
- Guaranteed score increases
- Automated recommendations

---

### 2. Credit Repair Readiness Notes

| Research Category | Route | Use |
|-------------------|-------|-----|
| credit_repair | credit_readiness_knowledge | Dispute readiness guardrails, FCRA/FDCPA awareness |

**Expected admin note output:**
- Credit repair readiness assessment
- Dispute workflow planning notes
- Compliance flags review

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for readiness assessment
- Why it matters for GoClear
- Client-facing status: no

**Blocked client-facing output:**
- Dispute letters
- Bureau contact
- Guaranteed deletions
- Score-increase promises

---

### 3. Business Setup Checklist

| Research Category | Route | Use |
|-------------------|-------|-----|
| business_setup | business_setup_checklist | Entity setup readiness, EIN/DUNS/NAICS education |

**Expected admin note output:**
- Business setup readiness checklist
- Missing items identification
- Next steps for entity formation

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for readiness assessment
- Why it matters for GoClear
- Client-facing status: no

**Blocked client-facing output:**
- Legal advice
- Tax advice
- Guaranteed funding from setup

---

### 4. Business Funding Readiness Checklist

| Research Category | Route | Use |
|-------------------|-------|-----|
| business_funding | funding_readiness_plan | Funding readiness assessment, pre-application notes |

**Expected admin note output:**
- Funding readiness assessment
- Missing documentation identification
- Readiness score input

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for readiness assessment
- Why it matters for GoClear
- Client-facing status: no

**Blocked client-facing output:**
- Guaranteed approval
- Specific rate/term promises
- Automated applications

---

### 5. Fundability Checklist

| Research Category | Route | Use |
|-------------------|-------|-----|
| business_setup | business_setup_checklist | Bankability/fundability readiness |

**Expected admin note output:**
- Fundability readiness assessment
- Bankability improvement notes
- Readiness score input

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for readiness assessment
- Why it matters for GoClear
- Client-facing status: no

**Blocked client-facing output:**
- Guaranteed funding
- Specific lender recommendations

---

### 6. Affiliate/Referral Review

| Research Category | Route | Use |
|-------------------|-------|-----|
| affiliates | affiliate_offer_approval | Affiliate offer evaluation |

**Expected admin note output:**
- Affiliate offer evaluation
- Client value assessment
- Compliance check (FTC disclosure)

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for affiliate use
- Why it matters for GoClear
- Client-facing status: no

**Blocked client-facing output:**
- Unapproved promotions
- Activated referral links

---

### 7. Client Education Drafts

| Research Category | Route | Use |
|-------------------|-------|-----|
| client_education | client_education_draft | Education content drafting |

**Expected admin note output:**
- Education content draft
- Compliance review notes
- Plain-language framing

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for education use
- Why it matters for GoClear
- Client-facing status: no

**Blocked client-facing output:**
- All client education until approved
- Specific financial advice
- Guaranteed outcomes

---

### 8. Admin Notes

| Research Category | Route | Use |
|-------------------|-------|-----|
| manual_notes | manual_review_queue | Internal operations notes |

**Expected admin note output:**
- Internal workflow documentation
- Process guidance
- Operational notes

**Expected Ray Review output:**
- Source artifact reference
- Recommendation for internal use
- Why it matters for GoClear
- Client-facing status: no

---

### 9. Ray Review Proposals

All workflow outputs generate Ray Review proposals with:
- Source artifact reference
- Recommendation
- Why it matters for GoClear
- Client-facing status: no
- Approval required: yes
- Blocked actions: send, publish, charge, trade, automated disputes, direct lender applications, guaranteed approvals

---

## Approval Gate Checklist

For each test profile processed:

- [ ] Profile is hypothetical (not real client)
- [ ] All outputs are admin-only
- [ ] No client-facing content generated
- [ ] No Supabase connection used
- [ ] No external API calls made
- [ ] No send/publish/charge/trade actions
- [ ] No outcome guarantees made
- [ ] All compliance flags reviewed
- [ ] All guarantee flags reviewed
- [ ] Ray Review draft generated
- [ ] Client-facing status: no
- [ ] Approval required: yes

---

## Testing Sequence

1. Create 3 hypothetical test profiles with varying characteristics
2. Run each profile through credit utilization review
3. Run each profile through business setup checklist
4. Run each profile through funding readiness checklist
5. Generate admin notes for each workflow
6. Generate Ray Review drafts for each workflow
7. Verify no client-facing output is generated
8. Verify all outputs are draft-only
9. Document results for Ray Review
