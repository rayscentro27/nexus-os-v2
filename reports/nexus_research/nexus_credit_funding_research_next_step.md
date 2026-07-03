# Nexus Credit & Funding Research Next Steps

**Generated**: 2026-07-03

---

## 10 Required Answers

### 1. Should Nexus have its own research engine?
**Yes.** Nexus needs a separate credit/funding research engine because:
- Credit/funding research is client-facing and compliance-sensitive
- It requires different approval gates than Alpha's business opportunity research
- It must be connected to GoClear workflows ($97 review, readiness scoring, client education)
- It has different data sources (lender criteria, grant databases, compliance notes)
- It must never be connected to Alpha's no-Supabase Phase 1

### 2. How is it different from Hermes Alpha?
| Dimension | Hermes Alpha | Nexus Credit & Funding |
|-----------|--------------|------------------------|
| Owner | Hermes Alpha | Nexus Hermes / GoClear |
| Supabase | No connection | Future approved pipeline |
| Client data | No access | Through secure workflow |
| Sources | YouTube, transcripts, tool research | Credit/funding research, compliance, grants |
| Outputs | Opportunity scorecards, marketing drafts | Readiness checklists, client education, funding recommendations |
| Approval | Ray Review for external use | Ray Review for all client-facing |
| Compliance | Not required | Required for all credit/funding |
| UI | Alpha dashboard | Nexus admin panel |

### 3. What folders were created?
```
nexus_research/research_inbox/
├── credit_repair/README.md
├── credit_utilization/README.md
├── business_setup/README.md
├── business_funding/README.md
├── grants/README.md
├── lenders/README.md
├── affiliates/README.md
├── compliance/README.md
├── client_education/README.md
└── manual_notes/README.md
```

### 4. Are there real artifacts yet?
**No.** All 10 inbox subdirectories contain only README files explaining rules and categories. No research artifacts have been collected. This is intentional — the inbox is empty by design until real research is added.

### 5. What research should Ray add first?
Priority order:
1. **Credit utilization research** — directly affects $97 review scoring
2. **Business setup research** — LLC, EIN, DUNS, NAICS requirements
3. **FCRA/FDCPA compliance notes** — currently missing, critical for dispute workflow
4. **Business funding basics** — credit cards, lines of credit, SBA overview
5. **Grant databases** — federal, state, minority business grants
6. **Bank affiliate research** — Bluevine, Mercury, Relay terms and requirements
7. **Credit monitoring options** — SmartCredit, IdentityIQ comparison
8. **Client education drafts** — credit report reading, utilization basics

### 6. What should become client-facing later?
After Ray Review approval:
- Credit utilization education (general, not specific advice)
- Business setup checklist overview
- Fundability checklist overview
- $97 review report (already exists, needs real data)
- Credit monitoring options (general overview)
- Business bank account options (general overview)
- Grant opportunity overview (general)

### 7. What must remain admin-only?
- Lender matching notes
- Dispute strategy recommendations
- Funding application preparation
- Compliance audit notes
- Affiliate offer evaluation
- Credit report analysis details
- Business profile scoring details
- Specialist handoff drafts
- All research artifacts before approval

### 8. What requires Ray Review?
Everything client-facing:
- All credit repair recommendations
- All funding recommendations
- All lender referrals
- All grant recommendations
- All dispute letter content
- All affiliate promotions
- All compliance note updates
- All client education content
- All fundability score changes
- All business setup recommendations

### 9. Should this connect to Supabase now or later?
**Later.** Current design:
- Phase 1: Local-only, no Supabase connection
- Phase 2: Research collection (still local)
- Phase 3: Adapter build (still local)
- Phase 4: Supabase connection (only after explicit approval, secure workflow built, tenant isolation verified)

### 10. Recommended next prompt
**"Build Nexus Credit & Funding Research Adapter v1 for one Ray-approved local Markdown artifact, draft-only and approval-gated."**

This adapter would:
- Read one local Markdown file from `nexus_research/research_inbox/`
- Classify it using the artifact schema
- Generate admin notes
- Generate a draft recommendation
- Require Ray Review before any output
- Remain local-only, no Supabase, no external connections

---

## Implementation Roadmap

### Immediate (This Session)
- ✅ Audit completed
- ✅ Architecture designed
- ✅ Inbox structure created
- ✅ Schema defined
- ✅ Routing planned
- ✅ Approval gates defined
- ✅ UI placement planned
- ✅ Tests written
- ✅ Verification passed
- ✅ Reports created

### Short-Term (Next Session)
- Build Nexus Credit & Funding Research Adapter v1
- Add first real research artifact (one credit utilization article)
- Test artifact classification and routing
- Verify approval gate works

### Medium-Term (Future)
- Populate all 10 inbox categories with real research
- Build research dashboard UI
- Build detail page UI
- Connect to $97 review workflow
- Build client education portal
- Add FCRA/FDCPA compliance notes

### Long-Term (Future)
- Connect to Supabase (approved pipeline)
- Build lender matching notes
- Build grant opportunity database
- Build affiliate offer evaluation system
- Build compliance audit system

---

## Risk Summary

| Risk | Mitigation | Status |
|------|------------|--------|
| Alpha accidentally accesses client data | No Supabase connection | ✅ Mitigated |
| Nexus makes unauthorized credit claims | Compliance classifiers, Ray Review gates | ✅ Designed |
| Research artifacts contain false information | Evidence quality scoring, compliance review | ✅ Designed |
| Affiliate promotions without approval | Approval gates, all programs `not_applied` | ✅ Designed |
| Funding guarantees | Explicit disclaimers, no lender connections | ✅ Designed |
| Legal advice without license | Education-only framing, compliance notes | ✅ Designed |
