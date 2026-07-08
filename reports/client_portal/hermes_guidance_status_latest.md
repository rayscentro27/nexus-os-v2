# Hermes Guidance Status

**Generated:** 2026-07-07

## Dynamic Guidance (commit f97e1ac)

- **Generator:** `clientGuidance.ts` ✓
- **Integration:** `ClientPortalShell.jsx` derives statuses from `clientPortalData` ✓
- **Fallback:** Static guidance when no status data ✓

## Guidance Triggers Verified

| Trigger | Condition | Guidance |
|---------|-----------|----------|
| Missing credit report | !creditReportUploaded | "Upload your credit report" |
| Missing address proof | !addressVerified | "Upload proof of address" |
| Missing identity | !identityVerified | "Verify your identity" |
| High utilization | creditProfileReadiness < 60 | "Reduce credit utilization" |
| Negative items | creditRepairProgress < 50 | "Review negative items" |
| No business bank | !businessBankAccount | "Open a business bank account" |
| No revenue docs | !revenueDocuments | "Upload revenue documentation" |
| Admin review needed | underReviewDocuments.length > 0 | "Your file is under review" |
| Low readiness | readinessScore < 50 | "Focus on top blockers" |

## Safety

- No guarantees ✓
- No external model calls for client-facing guidance ✓
- Conservative language ✓
- Advisory only (not decisions) ✓

## Blockers

- None.
