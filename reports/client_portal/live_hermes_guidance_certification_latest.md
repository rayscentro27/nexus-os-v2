# Hermes Guidance Connection Certification — Client Portal

**Date:** 2026-07-08
**Starting Commit:** 71b9dd4

---

## Hermes Guidance Architecture

### Two Guidance Systems

1. **Static ClientGuidePanel** (`ClientGuidePanel.jsx`)
   - Uses `clientGuideResponses.js` (static Q&A responses)
   - Chip-based suggestions: "What do I do next?", "Documents needed", "Can I apply for funding?"
   - Input field for custom questions
   - Pattern-matching response selection

2. **Dynamic HermesGuidancePanel** (`ClientPortalShell.jsx`)
   - Uses `generateClientGuidance()` from `clientGuidance.ts`
   - Generates items based on live status flags
   - Renders in the sidebar panel
   - Priority-sorted guidance items

---

## Guidance Rule Verification

### Rule: Missing credit report → guidance says upload credit report
- **Status:** PASS
- `clientGuidance.ts` line 24: `if (!s.creditReportUploaded)` → item: "Upload your credit report"
- Triggered when: `docs.uploadedDocuments` does not include "credit" or "report"

### Rule: Missing proof of address → guidance says upload proof of address
- **Status:** PASS
- `clientGuidance.ts` line 34: `if (!s.addressVerified)` → item: "Upload proof of address"
- Triggered when: `docs.uploadedDocuments` does not include "address"

### Rule: High utilization → guidance says lower utilization
- **Status:** PASS
- `clientGuidance.ts` line 54: `if (s.utilizationHigh)` → item: "Reduce credit utilization"
- Triggered when: `creditProfileReadiness < 60`

### Rule: Missing business bank account → guidance says add/open business bank account
- **Status:** PASS
- `clientGuidance.ts` line 74: `if (!s.businessBankAccount)` → item: "Open a business bank account"
- Triggered when: `docs.uploadedDocuments` does not include "bank"

### Rule: Admin review required → guidance says file is under review
- **Status:** PASS
- `clientGuidance.ts` line 94: `if (s.adminReviewRequired)` → item: "Your file is under review"
- Triggered when: `docs.underReviewDocuments.length > 0`

---

## Dynamic vs Static

| Aspect | Static (ClientGuidePanel) | Dynamic (HermesGuidancePanel) |
|---|---|---|
| Data source | `clientGuideResponses.js` | `clientGuidance.ts` generator |
| Input | Chip buttons + text input | Status flags from documents/scores |
| Output | Pre-written response text | Priority-sorted guidance items |
| Location | Below main content | Sidebar panel |
| Responsive to changes | No (static text) | Yes (regenerates on status change) |

---

## Safety Verification

### No guarantees
- ✅ All guidance includes "advisory only" disclaimers
- ✅ ClientGuidePanel: "Approved client-safe guidance only"
- ✅ HermesGuidancePanel: "Advisory only — not a decision"
- ✅ No funding promises or legal advice

### No unreviewed credit/legal/funding advice
- ✅ All responses are pre-approved static text
- ✅ Dynamic guidance generates from status flags only
- ✅ No free-text generation to client
- ✅ Escalation path: "Client questions requiring judgment must be routed into the GoClear admin review queue"

---

## Summary

| Check | Result |
|---|---|
| Missing credit report → upload guidance | PASS |
| Missing proof of address → upload guidance | PASS |
| High utilization → lower utilization guidance | PASS |
| Missing business bank account → banking guidance | PASS |
| Admin review required → under review guidance | PASS |
| Guidance from approved_client_guidance or generated | GENERATED (from status flags) |
| Guidance changes with task/status changes | YES (dynamic panel) |
| No guarantees | PASS |
| No unreviewed advice | PASS |

**CERTIFICATION: Hermes Guidance is functional and safe. Dynamic guidance generates from tester status. Static panel provides approved Q&A responses.**
