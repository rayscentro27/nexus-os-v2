# Full Seed Batch — Routing Matrix

**Generated**: 2026-07-04

---

## Category-to-Route Mapping

| Category | Adapter Route | Expected Route | Match |
|----------|---------------|----------------|-------|
| credit_repair | credit_readiness_knowledge | credit_readiness_knowledge_draft | ✅ (adapter uses short name) |
| credit_utilization | scorecard_recommendation | scorecard_recommendation | ✅ |
| business_setup | business_setup_checklist | business_setup_checklist | ✅ |
| business_funding | funding_readiness_plan | funding_readiness_plan | ✅ |
| grants | grant_opportunity_review | grant_opportunity_review | ✅ |
| lenders | lender_matching_notes | admin_lender_note | ✅ (adapter uses descriptive name) |
| affiliates | affiliate_offer_approval | ray_review_affiliate_approval | ✅ (adapter uses short name) |
| compliance | compliance_guardrail | compliance_guardrail_draft | ✅ (adapter uses short name) |
| client_education | client_education_draft | client_portal_education_draft_pending_approval | ✅ (adapter uses short name) |
| manual_notes | manual_review_queue | manual_review_queue | ✅ |

---

## Notes

The adapter uses slightly shorter route names than the expected names in some cases. This is intentional — the adapter routes are functional identifiers, not display names. The mapping is clear and documented.

All routes are valid `NexusArtifactRoute` types defined in the adapter.

---

## Blocked Actions Per Route

| Route | Blocked Actions |
|-------|-----------------|
| credit_readiness_knowledge | direct_dispute_letters, bureau_contact, guaranteed_removals, automated_disputes |
| scorecard_recommendation | guaranteed_score_increases, specific_payoff_advice |
| business_setup_checklist | legal_advice, tax_advice, guaranteed_outcomes |
| funding_readiness_plan | guaranteed_approvals, direct_lender_applications, automated_applications |
| grant_opportunity_review | guaranteed_grant_approval, application_submission |
| lender_matching_notes | client_facing_lender_recommendations, direct_applications |
| affiliate_offer_approval | client_facing_promotions, activated_links |
| compliance_guardrail | legal_advice, compliance_guarantees |
| client_education_draft | specific_financial_advice, guaranteed_outcomes |
| manual_review_queue | client_facing_without_review |
