# SmartCredit Import Path — Latest

**Date:** 2026-07-13
**Status:** Decision Document — No Integration Yet

---

## Recommended Near-Term Import Path (Do Now)

1. **Client uses recommended credit monitoring resource** (SmartCredit, IdentityIQ, AnnualCreditReport.com, or similar)
2. **Client downloads/saves report as PDF/HTML/TXT** from the monitoring dashboard
3. **Client uploads report to Nexus** via `/client/documents` upload panel
4. **Nexus extracts text** from the PDF where possible (pypdf for text-based, OCR for scanned)
5. **Nexus parses structured items** (accounts, inquiries, utilization, negative candidates)
6. **Specialist confirms/edits items** in Credit Specialist Workbench
7. **Nexus generates dispute strategy suggestions** for confirmed items
8. **Nexus generates draft letter previews** for specialist review
9. **Client approves letters** before any mailing request
10. **DocuPost sends only after all approvals** (future integration)

This path:
- Requires no API keys
- Requires no partner agreements
- Respects data privacy (no SSN/DOB/EIN collection)
- Works today with existing Nexus upload flow
- Proves the engine end-to-end

---

## Future Options (Postpone)

### Affiliate Tracking Link
- Create a SmartCredit affiliate/referral link
- Client clicks link, creates SmartCredit account
- Client downloads report, uploads to Nexus
- **Prerequisite:** SmartCredit affiliate agreement, tracking pixel/link setup
- **Priority:** Low — not needed for engine proof

### Report Import Instructions
- Create step-by-step instructions for client to export report from SmartCredit/IdentityIQ
- Include screenshots and format guidance
- **Prerequisite:** None — can create now
- **Priority:** Medium — improves client onboarding

### Pasted HTML/TXT Parser
- Allow client to paste raw HTML or text from credit report
- Parse pasted content directly without PDF extraction
- **Prerequisite:** None — frontend form + parser
- **Priority:** Medium — useful fallback for non-PDF reports

### Provider Webhook/API
- SmartCredit/IdentityIQ webhook integration for automatic report import
- **Prerequisite:** Verified partner access, API keys, legal agreement
- **Priority:** Low — defer until partner access is verified

---

## Decision

**Do not integrate SmartCredit API yet.** Focus on proving the local engine flow with uploaded PDFs first. SmartCredit integration is a scaling optimization, not an engine prerequisite.
